/*
  This file is part of CanFestival, a library implementing CanOpen
  Stack.

  Copyright (C): Edouard TISSERANT and Francis DUPIN

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
  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307
  USA
*/

/*!
** @file   emcy.c
** @author Luis Jimenez
** @date   Wed Sep 26 2007
**
** @brief Definitions of the functions that manage EMCY (emergency) messages
**
**
*/

#include <data.h>
#include "emcy.h"
#include "canfestival.h"



UNS32 OnNumberOfErrorsUpdate(CO_Data* d, const indextable * unsused_indextable, UNS8 unsused_bSubindex);
UNS8 sendEMCY(CO_Data* d, UNS32 cob_id, UNS16 errCode, UNS8 errRegister);


/*! This is called when Index 0x1003 is updated.
**
**
** @param d
** @param unsused_indextable
** @param unsused_bSubindex
**
** @return
**/
UNS32 OnNumberOfErrorsUpdate(CO_Data* d, const indextable * unsused_indextable, UNS8 unsused_bSubindex)
{
	UNS8 index;
  // if 0, reset Pre-defined Error Field
  // else, don't change and give an abort message (eeror code: 0609 0030h)
	if (*d->error_number == 0)
		for (index = 0; index < d->error_history_size; ++index)
			*(d->error_first_element + index) = 0;		/* clear all the fields in Pre-defined Error Field (1003h) */
	else
		;// abort message
  return 0;
}

/*! start the EMCY mangagement.
**
**
** @param d
**/
void emergencyInit(CO_Data* d)
{
  RegisterSetODentryCallBack(d, 0x1003, 0x00, &OnNumberOfErrorsUpdate);

  *d->error_number = 0;
}

/*!
**
**
** @param d
**/
void emergencyStop(CO_Data* d)
{
  
}

/*!                                                                                                
 **                                                                                                 
 **                                                                                                 
 ** @param d                                                                                        
 ** @param cob_id                                                                                   
 **                                                                                                 
 ** @return                                                                                         
 **/  
UNS8 sendEMCY(CO_Data* d, UNS32 cob_id, UNS16 errCode, UNS8 errRegister)
{
	Message m;
  
	MSG_WAR(0xA001, "sendEMCY", 0);
  
	m.cob_id.w = cob_id ;
	m.rtr = NOT_A_REQUEST;
	m.len = 8;
	m.data[0] = errCode & 0xFF;        /* LSB */
	m.data[1] = (errCode >> 8) & 0xFF; /* MSB */
	m.data[2] = errRegister;
	m.data[3] = 0;		/* Manufacturer specific Error Field still not implemented */
	m.data[4] = 0;
	m.data[5] = 0;
	m.data[6] = 0;
	m.data[7] = 0;
  
	return canSend(d->canHandle,&m);
}

/*! Sets a new error with code errCode. Also sets corresponding bits in Error register (1001h)
 **                                                                                                 
 **  
 ** @param d
 ** @param errCode Code of the error                                                                                        
 ** @param errRegister Bits of Error register (1001h) to be set.
 ** @return 1 if error, 0 if successful
 */
UNS8 EMCY_setError(CO_Data* d, UNS16 errCode, UNS8 errRegMask)
{
	UNS8 index;
	UNS8 errRegister_tmp;
	
	for (index = 0; index < EMCY_MAX_ERRORS; ++index)
	{
		if (d->error_data[index].errCode == errCode)		/* error already registered */
		{
			if (d->error_data[index].active)
			{
				MSG_WAR(0xA002, "EMCY message already sent", 0);
				return 0;
			} else d->error_data[index].active = 1;		/* set as active error */
			break;
		}
	}
	
	if (index == EMCY_MAX_ERRORS)		/* if errCode not already registered */
		for (index = 0; index < EMCY_MAX_ERRORS; ++index) if (d->error_data[index].active == 0) break;	/* find first inactive error */
	
	if (index == EMCY_MAX_ERRORS)		/* error_data full */
	{
		MSG_ERR(0xA003, "error_data full", 0);
		return 1;
	}
	
	d->error_data[index].errCode = errCode;
	d->error_data[index].errRegMask = 1;
	d->error_data[index].active = 1;
	
	/* set the new state in the error state machine */
	d->error_state = Error_occurred;

	/* set Error Register (1001h) */
	for (index = 0, errRegister_tmp = 0; index < EMCY_MAX_ERRORS; ++index)
		if (d->error_data[index].active == 1) errRegister_tmp |= d->error_data[index].errRegMask;
	*d->error_register = errRegister_tmp;
	
	/* set Pre-defined Error Field (1003h) */
	for (index = d->error_history_size - 1; index > 0; --index)
		*(d->error_first_element + index) = *(d->error_first_element + index - 1);
	*(d->error_first_element) = (UNS32)errCode;
	if(*d->error_number < d->error_history_size) ++(*d->error_number);
	
	/* send EMCY message */
	if (d->CurrentCommunicationState.csEmergency)
		return sendEMCY(d, *d->bDeviceNodeId + 0x080, errCode, *d->error_register);
	else return 1;
}

/*! Deletes error errCode. Also clears corresponding bits in Error register (1001h)
 **                                                                                                 
 **  
 ** @param d
 ** @param errCode Code of the error                                                                                        
 ** @param errRegister Bits of Error register (1001h) to be set.
 ** @return 1 if error, 0 if successful
 */
void EMCY_errorRecovered(CO_Data* d, UNS16 errCode)
{
	UNS8 index;
	UNS8 errRegister_tmp;
	UNS8 anyActiveError = 0;
	
	for (index = 0; index < EMCY_MAX_ERRORS; ++index)
		if (d->error_data[index].errCode == errCode) break;		/* find the position of the error */

	
	if ((index != EMCY_MAX_ERRORS) && (d->error_data[index].active == 1))
	{
		d->error_data[index].active = 0;
		
		/* set Error Register (1001h) and check error state machine */
		for (index = 0, errRegister_tmp = 0; index < EMCY_MAX_ERRORS; ++index)
			if (d->error_data[index].active == 1)
			{
				anyActiveError = 1;
				errRegister_tmp |= d->error_data[index].errRegMask;
			}
		if(anyActiveError == 0)
		{
			d->error_state = Error_free;
			/* send a EMCY message with code "Error Reset or No Error" */
			if (d->CurrentCommunicationState.csEmergency)
				sendEMCY(d, *d->bDeviceNodeId + 0x080, 0x0000, 0x00);
		}
		*d->error_register = errRegister_tmp;
	}
	else
		MSG_WAR(0xA004, "recovered error was not active", 0);
}

/*! This function is responsible to process an EMCY canopen-message.
 **
 **
 ** @param d
 ** @param m The CAN-message which has to be analysed.
 **
 **/
void proceedEMCY(CO_Data* d, Message* m)
{
	UNS8 nodeID;
	UNS16 errCode;
	UNS8 errReg;
	
	MSG_WAR(0xA005, "EMCY received. Proceed. ", 0);
  
	/* Test if the size of the EMCY is ok */
	if ( m->len != 8) {
		MSG_ERR(0xA006, "Error size EMCY. CobId  : ", m->cob_id.w);
		return;
	}
	
	/* post the received EMCY */
	nodeID = m->cob_id.w & 0x7F;
	errCode = m->data[0] | ((UNS16)m->data[1] << 8);
	errReg = m->data[2];
	(*d->post_emcy)(nodeID, errCode, errReg);
}

void _post_emcy(UNS8 nodeID, UNS16 errCode, UNS8 errReg){}
