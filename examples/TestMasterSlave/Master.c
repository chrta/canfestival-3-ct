/*
This file is part of CanFestival, a library implementing CanOpen Stack. 

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
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
*/

#include "Master.h"
#include "Slave.h"
#include "TestMasterSlave.h"

/*****************************************************************************/
void TestMaster_heartbeatError(UNS8 heartbeatID)
{
	eprintf("TestMaster_heartbeatError %d\n", heartbeatID);
}

/*****************************************************************************/
void TestMaster_SDOtimeoutError (UNS8 line)
{
	eprintf("TestMaster_SDOtimeoutError %d\n", line);
}

/********************************************************
 * ConfigureSlaveNode is responsible to
 *  - setup master RPDO 1 to receive TPDO 1 from id 2
 *  - setup master RPDO 2 to receive TPDO 2 from id 2
 ********************************************************/
void TestMaster_initialisation()
{
	UNS32 PDO1_COBID = 0x0182; 
	UNS32 PDO2_COBID = 0x0282;
	UNS8 size = sizeof(UNS32); 

	eprintf("TestMaster_initialisation\n");

	/*****************************************
	 * Define RPDOs to match slave ID=2 TPDOs*
	 *****************************************/
	setODentry( &TestMaster_Data, /*CO_Data* d*/
			0x1400, /*UNS16 index*/
			0x01, /*UNS8 subind*/ 
			&PDO1_COBID, /*void * pSourceData,*/ 
			&size, /* UNS8 * pExpectedSize*/
			RW);  /* UNS8 checkAccess */
			
	setODentry( &TestMaster_Data, /*CO_Data* d*/
			0x1401, /*UNS16 index*/
			0x01, /*UNS8 subind*/ 
			&PDO2_COBID, /*void * pSourceData,*/ 
			&size, /* UNS8 * pExpectedSize*/
			RW);  /* UNS8 checkAccess */
}

/********************************************************
 * ConfigureSlaveNode is responsible to
 *  - setup slave TPDO 1 transmit time
 *  - setup slave TPDO 2 transmit time
 *  - switch to operational mode
 *  - send NMT to slave
 ********************************************************
 * This an example of :
 * Network Dictionary Access (SDO) with Callback 
 * Slave node state change request (NMT) 
 ********************************************************
 * This is called first by TestMaster_preOperational
 * then it called again each time a SDO exchange is
 * finished.
 ********************************************************/
static void ConfigureSlaveNode(CO_Data* d, UNS8 nodeId)
{
	// Step counts number of times ConfigureSlaveNode is called
	static step = 1;
	
	UNS8 Transmission_Type = 0x01; 
	UNS32 abortCode;
	UNS8 res;
	eprintf("Master : ConfigureSlaveNode %2.2x\n", nodeId);

	switch(step++){
		case 1: /*First step : setup Slave's TPDO 1 to be transmitted on SYNC*/
			eprintf("Master : set slave %2.2x TPDO 1 transmit type\n", nodeId);
			res = writeNetworkDictCallBack (d, /*CO_Data* d*/
					*TestSlave_Data.bDeviceNodeId, /*UNS8 nodeId*/
					0x1800, /*UNS16 index*/
					0x02, /*UNS8 subindex*/
					1, /*UNS8 count*/
					0, /*UNS8 dataType*/
					&Transmission_Type,/*void *data*/
					ConfigureSlaveNode); /*SDOCallback_t Callback*/			break;
		case 2:	/*Second step*/
			/*check and warn for previous slave OD access error*/
			if(getWriteResultNetworkDict (d, nodeId, &abortCode) != SDO_FINISHED)
				eprintf("Master : Couldn't set slave %2.2x TPDO 1 transmit type. AbortCode :%4.4x \n", nodeId, abortCode);

			/* Finalise last SDO transfer with this node */
			closeSDOtransfer(&TestMaster_Data,
					*TestSlave_Data.bDeviceNodeId,
					SDO_CLIENT);
					
			/*Setup Slave's TPDO 1 to be transmitted on SYNC*/
			eprintf("Master : set slave %2.2x TPDO 2 transmit type\n", nodeId);
			writeNetworkDictCallBack (d, /*CO_Data* d*/
					*TestSlave_Data.bDeviceNodeId, /*UNS8 nodeId*/
					0x1801, /*UNS16 index*/
					0x02, /*UNS16 index*/
					1, /*UNS8 count*/
					0, /*UNS8 dataType*/
					&Transmission_Type,/*void *data*/
					ConfigureSlaveNode); /*SDOCallback_t Callback*/
			break;
		case 3: /*Last step*/
			/*check and warn for previous slave OD access error*/
			if(getWriteResultNetworkDict (d, nodeId, &abortCode) != SDO_FINISHED)
				eprintf("Master : Couldn't set slave %2.2x TPDO 2 transmit type. AbortCode :%4.4x \n", nodeId, abortCode);

			/* Finalise last SDO transfer with this node */
			closeSDOtransfer(&TestMaster_Data,
					*TestSlave_Data.bDeviceNodeId,
					SDO_CLIENT);

			/* Put the master in operational mode */
			setState(d, Operational);
			  
			/* Ask slave node to go in operational mode */
			masterSendNMTstateChange (d, nodeId, NMT_Start_Node);
	}
			
}

void TestMaster_preOperational()
{

	eprintf("TestMaster_preOperational\n");
	ConfigureSlaveNode(&TestMaster_Data, 2);
	
}

void TestMaster_operational()
{
	eprintf("TestMaster_operational\n");
}

void TestMaster_stopped()
{
	eprintf("TestMaster_stopped\n");
}

void TestMaster_post_sync()
{
	eprintf("TestMaster_post_sync\n");
	eprintf("Master: %d %d %d %d\n",MasterMap1, MasterMap2, MasterMap3, MasterMap4);
}

char query_result = 0;
char waiting_answer = 0;

void TestMaster_post_TPDO()
{
	eprintf("TestMaster_post_TPDO\n");

//	{
//		char zero = 0;
//		if(MasterMap4 > 0x80){
//			writeNetworkDict (
//				&TestMaster_Data,
//				TestSlave_Data->bDeviceNodeId,
//				0x2002,
//				0x00,
//				1,
//				0,
//				&zero); 
//		}
//	}

	if(waiting_answer){
		UNS32 abortCode;			
		UNS8 size;			
		switch(getReadResultNetworkDict (
			&TestMaster_Data, 
			*TestSlave_Data.bDeviceNodeId,
			&query_result,
			&size,
			&abortCode))
		{
			case SDO_FINISHED:
				/* Do something with result here !!*/
				eprintf("Got SDO answer (0x2002, 0x00), %d %d\n",query_result,size);
			case SDO_ABORTED_RCV:
			case SDO_ABORTED_INTERNAL:
			case SDO_RESET:
				waiting_answer = 0;
				closeSDOtransfer(
					&TestMaster_Data,
					*TestSlave_Data.	bDeviceNodeId,
					SDO_CLIENT);
			break;
			case SDO_DOWNLOAD_IN_PROGRESS:
			case SDO_UPLOAD_IN_PROGRESS:
			break;
		}
	}else if(MasterMap1 % 10 == 0){
		readNetworkDict (
			&TestMaster_Data,
			*TestSlave_Data.bDeviceNodeId,
			0x2002,
			0x00,
			0);
		waiting_answer = 1;
	}
		
}
