/*
This file is part of CanFestival, a library implementing CanOpen Stack.

Copyright (C): Edouard TISSERANT and Francis DUPIN
Modified by: Jaroslav Fojtik

See COPYING file for copyrights details.

This library is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 2.1 of the License, or (at your option) any later version.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with this library; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
*/

#if defined(WIN32) && !defined(__CYGWIN__)
#define usleep(micro) Sleep(micro%1000 ? (micro/1000) + 1 : (micro/1000))
#else
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <fcntl.h>
#endif

#include "cancfg.h"
#include "can_driver.h"
#include "def.h"


#define VERSION_2

/* dummy implementation for older version. */
#ifndef VERSION_2
void CAN_SetRcvEvent(HANDLE hEventx)
{
  SetEvent(hEventx);
}
#endif




#ifndef extra_PCAN_init_params
	#define extra_PCAN_init_params /**/
#else
	long int print_getenv(const char* pcanparam)
	{
		char* param=NULL;
		long int res=0;

		param = getenv(pcanparam);
		if(param != NULL){
			res = strtol(param,NULL,0);
		}
		else
			printf("Environment variable %s not defined !\n", pcanparam);
		printf("Found environment variable %s : %ld\n", pcanparam ,res);
		return res;
	}
	#define extra_PCAN_init_params\
		,print_getenv("PCANHwType")\
		,print_getenv("PCANIO_Port")\
		,print_getenv("PCANInterupt")
#endif


static s_BOARD *first_board = NULL;
//Create the Event for the first board
HANDLE hEvent1 = NULL;
CRITICAL_SECTION InitLock1;
CRITICAL_SECTION InitLock2;


#ifdef PCAN2_HEADER_
  static s_BOARD *second_board = NULL;
  HANDLE hEvent2 = NULL;
#endif

// Define for rtr CAN message
#define CAN_INIT_TYPE_ST_RTR MSGTYPE_STANDARD | MSGTYPE_RTR

/***************************************************************************/
static int TranslateBaudeRate(char* optarg)
{
	if(!strcmp( optarg, "1M")) return CAN_BAUD_1M;
	if(!strcmp( optarg, "500K")) return CAN_BAUD_500K;
	if(!strcmp( optarg, "250K")) return CAN_BAUD_250K;
	if(!strcmp( optarg, "125K")) return CAN_BAUD_125K;
	if(!strcmp( optarg, "100K")) return CAN_BAUD_100K;
	if(!strcmp( optarg, "50K")) return CAN_BAUD_50K;
	if(!strcmp( optarg, "20K")) return CAN_BAUD_20K;
	if(!strcmp( optarg, "10K")) return CAN_BAUD_10K;
	if(!strcmp( optarg, "5K")) return CAN_BAUD_5K;
	if(!strcmp( optarg, "none")) return 0;
	return 0x0000;
}

static UNS8 canInit (s_BOARD *board)
{
	int baudrate;
	int ret = 0;

#ifdef PCAN2_HEADER_
	// if not the first handler
	if(second_board == (s_BOARD *)board) {
		if(hEvent2==NULL)
		{	/* Create the Event for the first board */
		  hEvent2 = CreateEvent(NULL, // lpEventAttributes
							FALSE,  // bManualReset
							FALSE,  // bInitialState
							"");    // lpName
		  InitializeCriticalSection(&InitLock2);
		}

		EnterCriticalSection(&InitLock2);
		if(baudrate = TranslateBaudeRate(board->baudrate))
		{
		  ret = CAN2_Init(baudrate, CAN_INIT_TYPE_ST extra_PCAN_init_params);
		  if(ret != CAN_ERR_OK)
		  {
		    LeaveCriticalSection(&InitLock2);
		    return 0;
		  }
		}
		//Set Event Handle for CANReadExt
		CAN2_SetRcvEvent(hEvent2);
		LeaveCriticalSection(&InitLock2);
	}
	else
#endif
	if(first_board == (s_BOARD *)board) {
		//Create the Event for the first board
		if(hEvent1==NULL)
		{
		  hEvent1 = CreateEvent(NULL, // lpEventAttributes
							FALSE,  // bManualReset
							FALSE,  // bInitialState
							"");    // lpName
		  InitializeCriticalSection(&InitLock1);
                }

		EnterCriticalSection(&InitLock1);
		if(baudrate = TranslateBaudeRate(board->baudrate))
		{
		  ret = CAN_Init(baudrate, CAN_INIT_TYPE_ST extra_PCAN_init_params);
		  if(ret != CAN_ERR_OK)
		  {
		    LeaveCriticalSection(&InitLock1);
		    return 0;
		  }
		}
		//Set Event Handle for CANReadExt
		CAN_SetRcvEvent(hEvent1);
		LeaveCriticalSection(&InitLock1);
	}
	return 1;
}

/********* functions which permit to communicate with the board ****************/
UNS8 LIBAPI canReceive_driver(CAN_HANDLE fd0, Message * m)
{
static int HeavyCounter = 0;
	int ret=0;
	UNS8 data;
	TPCANMsg peakMsg;
#ifdef CAN_READ_EX
	TPCANTimestamp peakRcvTime;
#endif
	DWORD Res;
	DWORD result;
	// loop until valid message or fatal error
	do{
#ifdef PCAN2_HEADER_
		// if not the first handler
		if(second_board == (s_BOARD *)fd0) {
			//wait for CAN msg...
			result = WaitForSingleObject(hEvent2, INFINITE);
			if (result == WAIT_OBJECT_0)
				Res = CAN2_ReadEx(&peakMsg, &peakRcvTime);
				// Exit receive thread when handle is no more valid
				if(Res & CAN_ERRMASK_ILLHANDLE)
					return 1;
		}
		else
#endif

		// We read the queue looking for messages.
		if(first_board == (s_BOARD *)fd0) 
		{
#ifdef VERSION_2
			result = WaitForSingleObject(hEvent1, INFINITE);
			if (result == WAIT_OBJECT_0)
#endif
			{
#ifdef CAN_READ_EX
				Res = CAN_ReadEx(&peakMsg, &peakRcvTime);
#else
				Res = CAN_Read(&peakMsg);
#endif
				// Exit receive thread when handle is no more valid
#ifdef CAN_ERRMASK_ILLHANDLE
				if(Res & CAN_ERRMASK_ILLHANDLE) return 1;
#else
				if(Res & CAN_ERR_ILLHANDLE) return 1;
#endif				

#ifndef VERSION_2
				if(Res != CAN_ERR_OK) 
					result = WaitForSingleObject(hEvent1, 1);  	//pooling
#endif
			}
		}
#ifdef VERSION_2
		else
			Res = CAN_ERR_BUSOFF;
#endif
		
		// A message was received : we process the message(s)
		if(Res == CAN_ERR_OK)
		{			
		  switch(peakMsg.MSGTYPE)
		  {
		    case MSGTYPE_STATUS:
			  switch(peakMsg.DATA[3])
		          {
			    case CAN_ERR_BUSHEAVY: 
				      break;
		            case CAN_ERR_BUSOFF: 
			              printf ("Peak board read BUSOFF: re-init!!!\n");
				      canInit((s_BOARD*)fd0);
				      usleep(33);
				      break;
			  }
			  return peakMsg.DATA[3];	/* if something different that 11bit or rtr... problem */

		    case MSGTYPE_STANDARD:		/* bits of MSGTYPE_ */
		    case MSGTYPE_EXTENDED:
			  m->rtr = 0;
			  break;

		    case MSGTYPE_RTR:			/* bits of MSGTYPE_ */
			  m->rtr = 1;
			  break;

		    default: return CAN_ERR_OVERRUN;	/* If status, return status if 29bit, return overrun. */
		    
		    }

		   m->cob_id = peakMsg.ID;				
		   if (peakMsg.MSGTYPE == CAN_INIT_TYPE_ST)  /* bits of MSGTYPE_ */
                     m->rtr = 0;
		   else
		     m->rtr = 1;
		   m->len = peakMsg.LEN;		/* count of data bytes (0..8) */
		   for (data = 0; data < peakMsg.LEN; data++)
			m->data[data] = peakMsg.DATA[data];	/* data bytes, up to 8 */
#if defined DEBUG_MSG_CONSOLE_ON
			MSG("in : ");
			print_message(m);
#endif
		}
		else
		{
			// not benign error => fatal error
			if (!(Res & CAN_ERR_QRCVEMPTY
					|| Res & CAN_ERR_BUSLIGHT
					|| Res & CAN_ERR_BUSHEAVY))
			{
				printf ("canReceive returned error (%d)\n", Res);
				return 1;
			}
		}
	} while(Res != CAN_ERR_OK);
	return 0;
}

/***************************************************************************/
UNS8 LIBAPI canSend_driver(CAN_HANDLE fd0, Message const *m)
{
	UNS8 data;
	TPCANMsg peakMsg;
	peakMsg.ID = m->cob_id;	/* 11/29 bit code */
	if (m->rtr == 0)
	{
	  if(peakMsg.ID > 0x7FF)
		peakMsg.MSGTYPE = MSGTYPE_EXTENDED;	/* bits of MSGTYPE_ */
	  else
		peakMsg.MSGTYPE = MSGTYPE_STANDARD;	/* bits of MSGTYPE_ */
	}
	else	
		peakMsg.MSGTYPE = MSGTYPE_RTR;		/* bits of MSGTYPE_ */
	
	peakMsg.LEN = m->len;
	/* count of data bytes (0..8) */
	for (data = 0; data < m->len; data++)
		peakMsg.DATA[data] = m->data[data];	/* data bytes, up to 8 */

	do
	{
#ifdef PCAN2_HEADER_
		// if not the first handler
		if(second_board == (s_BOARD *)fd0)
		{
			errno = CAN2_Write (&peakMsg);
		}
		else
#endif
		if(first_board == (s_BOARD *)fd0)
			{
				errno = CAN_Write (&peakMsg);
			}
		else
			goto fail;
		if (errno)
		{
			if (errno == CAN_ERR_BUSOFF)
			{
				printf ("!!! Peak board write : re-init\n");
				canInit((s_BOARD*)fd0);
				usleep (10000);
			}
			usleep (1000);
		}
	}
	while (errno != CAN_ERR_OK);
#if defined DEBUG_MSG_CONSOLE_ON
	MSG("out : ");
	print_message(m);
#endif
	return 0;
fail:
	return 1;
}

/***************************************************************************/
UNS8 LIBAPI canChangeBaudRate_driver(CAN_HANDLE fd, char* baud)
{
	printf("canChangeBaudRate not yet supported by this driver\n");
	return 0;
}

/***************************************************************************/
LIBPUBLIC CAN_HANDLE LIBAPI canOpen_driver(s_BOARD * board)
{
  char* pEnd;
  int ret;

  //printf ("Board Busname=%d.\n",strtol(board->busname, &pEnd,0));
  if (strtol(board->busname, &pEnd,0) == 0)
  {
      first_board = board;
      //printf ("First Board selected\n");
      ret = canInit(board);
      if(ret)
    	  return (CAN_HANDLE)board;
  }
  #ifdef PCAN2_HEADER_
  if (strtol(board->busname, &pEnd,0) == 1)
  {
      second_board = board;
      //printf ("Second Board selected\n");
      ret = canInit(board);
      if(ret)
    	  return (CAN_HANDLE)board;
  }
  #endif
  return NULL;
}


/***************************************************************************/
int LIBAPI canClose_driver(CAN_HANDLE fd0)
{
#ifdef PCAN2_HEADER_
	// if not the first handler
	if(second_board == (s_BOARD *)fd0)
	{
		CAN2_SetRcvEvent(NULL);
		CAN2_Close ();		
		if(hEvent2)
		{
		  SetEvent(hEvent2);
		  CloseHandle(hEvent2);		
		  hEvent2 = NULL;
		}
		second_board = (s_BOARD *)NULL;
	}else
#endif
	if(first_board == (s_BOARD *)fd0)
	{
		CAN_SetRcvEvent(NULL);
		CAN_Close ();		
		if(hEvent1) 
		{
                  SetEvent(hEvent1);
		  CloseHandle(hEvent1);
		  hEvent1 = NULL;
                }
		first_board = (s_BOARD *)NULL;
	}
	return 0;
}
