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

#include <data.h>
#include "lifegrd.h"
#include "canfestival.h"

/* Prototypes for internals functions */
void ConsumerHearbeatAlarm(CO_Data* d, UNS32 id);
void ProducerHearbeatAlarm(CO_Data* d, UNS32 id);


/*****************************************************************************/
e_nodeState getNodeState (CO_Data* d, UNS8 nodeId)
{
	e_nodeState networkNodeState = d->NMTable[nodeId];
	return networkNodeState;
}

/*****************************************************************************/
/* The Consumer Timer Callback */
void ConsumerHearbeatAlarm(CO_Data* d, UNS32 id)
{
        /*MSG_WAR(0x00, "ConsumerHearbeatAlarm", 0x00);*/
	
	/* call heartbeat error with NodeId */
	(*d->heartbeatError)((UNS8)( ((d->ConsumerHeartbeatEntries[id]) & (UNS32)0x00FF0000) >> (UNS8)16 ));
}

/*****************************************************************************/
void proceedNODE_GUARD(CO_Data* d, Message* m )
{
  UNS8 nodeId = (UNS8) GET_NODE_ID((*m));
  
  if((m->rtr == 1) ) /* Notice that only the master can have sent this node guarding request */
  { /* Receiving a NMT NodeGuarding (request of the state by the master) */
    /*  only answer to the NMT NodeGuarding request, the master is not checked (not implemented) */
    if (nodeId == *d->bDeviceNodeId )
    {
      Message msg;
      msg.cob_id.w = *d->bDeviceNodeId + 0x700;
      msg.len = (UNS8)0x01;
      msg.rtr = 0;
      msg.data[0] = d->nodeState; 
      if (d->toggle)
      {
        msg.data[0] |= 0x80 ;
        d->toggle = 0 ;
      }
      else
        d->toggle = 1 ; 
      /* send the nodeguard response. */
      MSG_WAR(0x3130, "Sending NMT Nodeguard to master, state: ", d->nodeState);
      canSend(d->canHandle,&msg );
    }  

  }else{ /* Not a request CAN */

    MSG_WAR(0x3110, "Received NMT nodeId : ", nodeId);
    /* the slave's state receievd is stored in the NMTable */
      /* The state is stored on 7 bit */
    d->NMTable[nodeId] = (e_nodeState) ((*m).data[0] & 0x7F) ;
    
    /* Boot-Up frame reception */
    if ( d->NMTable[nodeId] == Initialisation)
      {
        /* The device send the boot-up message (Initialisation) */
        /* to indicate the master that it is entered in pre_operational mode */
        /* Because the  device enter automaticaly in pre_operational mode, */
        /* the pre_operational mode is stored */
/*        NMTable[bus_id][nodeId] = Pre_operational; */
        MSG_WAR(0x3100, "The NMT is a bootup from node : ", nodeId);
      }
      
    if( d->NMTable[nodeId] != Unknown_state ) {
        UNS8 index, ConsummerHeartBeat_nodeId ;
        for( index = (UNS8)0x00; index < *d->ConsumerHeartbeatCount; index++ )
        {
            ConsummerHeartBeat_nodeId = (UNS8)( ((d->ConsumerHeartbeatEntries[index]) & (UNS32)0x00FF0000) >> (UNS8)16 );
            if ( nodeId == ConsummerHeartBeat_nodeId )
            {
                TIMEVAL time = ( (d->ConsumerHeartbeatEntries[index]) & (UNS32)0x0000FFFF ) ;
            	/* Renew alarm for next heartbeat. */
            	DelAlarm(d->ConsumerHeartBeatTimers[index]);
            	d->ConsumerHeartBeatTimers[index] = SetAlarm(d, index, &ConsumerHearbeatAlarm, MS_TO_TIMEVAL(time), 0);
            }
        }
    }
  }
}

/*****************************************************************************/
/* The Consumer Timer Callback */
void ProducerHearbeatAlarm(CO_Data* d, UNS32 id)
{
	if(*d->ProducerHeartBeatTime)
	{
		Message msg;
		/* Time expired, the heartbeat must be sent immediately
		 * generate the correct node-id: this is done by the offset 1792
		 * (decimal) and additionaly
		 * the node-id of this device.
		 */
		msg.cob_id.w = *d->bDeviceNodeId + 0x700;
		msg.len = (UNS8)0x01;
		msg.rtr = 0;
		msg.data[0] = d->nodeState; /* No toggle for heartbeat !*/
		/* send the heartbeat */
      		MSG_WAR(0x3130, "Producing heartbeat: ", d->nodeState);
      		canSend(d->canHandle,&msg );
	}else{
		d->ProducerHeartBeatTimer = DelAlarm(d->ProducerHeartBeatTimer);
	}
}

/*****************************************************************************/
void heartbeatInit(CO_Data* d)
{
    UNS8 index; /* Index to scan the table of heartbeat consumers */

    d->toggle = 0;

    for( index = (UNS8)0x00; index < *d->ConsumerHeartbeatCount; index++ )
    {
        TIMEVAL time = (UNS16) ( (d->ConsumerHeartbeatEntries[index]) & (UNS32)0x0000FFFF ) ;
        /* MSG_WAR(0x3121, "should_time : ", should_time ) ; */
        if ( time )
        {
            	d->ConsumerHeartBeatTimers[index] = SetAlarm(d, index, &ConsumerHearbeatAlarm, MS_TO_TIMEVAL(time), 0);
        }
    }

    if ( *d->ProducerHeartBeatTime )
    {
    	TIMEVAL time = *d->ProducerHeartBeatTime;
    	d->ProducerHeartBeatTimer = SetAlarm(d, 0, &ProducerHearbeatAlarm, MS_TO_TIMEVAL(time), MS_TO_TIMEVAL(time));
    }
}

/*****************************************************************************/
void heartbeatStop(CO_Data* d)
{
    UNS8 index;
    for( index = (UNS8)0x00; index < *d->ConsumerHeartbeatCount; index++ )
    {
        d->ConsumerHeartBeatTimers[index + 1] = DelAlarm(d->ConsumerHeartBeatTimers[index + 1]);;
    }

    d->ProducerHeartBeatTimer = DelAlarm(d->ProducerHeartBeatTimer);;
}

void _heartbeatError(UNS8 heartbeatID){}
