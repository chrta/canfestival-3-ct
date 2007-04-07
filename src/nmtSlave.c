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

#include "nmtSlave.h"
#include "states.h"
#include "canfestival.h"

/*******************************************************************)*********/
/* put the slave in the state wanted by the master */	
void proceedNMTstateChange(CO_Data* d, Message *m)
{
  if( d->nodeState == Pre_operational ||
      d->nodeState == Operational ||
      d->nodeState == Stopped ) {
    
    MSG_WAR(0x3400, "NMT received. for node :  ", (*m).data[1]);
    
    /* Check if this NMT-message is for this node */
    /* byte 1 = 0 : all the nodes are concerned (broadcast) */
    	
    if( ( (*m).data[1] == 0 ) || ( (*m).data[1] == *d->bDeviceNodeId ) ){
      
      switch( (*m).data[0]){ /* command specifier (cs) */			
      case NMT_Start_Node:
        if ( (d->nodeState == Pre_operational) || (d->nodeState == Stopped) )
          setState(d,Operational);
        break; 
        
      case NMT_Stop_Node:
        if ( d->nodeState == Pre_operational ||
	     d->nodeState == Operational )
          setState(d,Stopped);
        break;
        
      case NMT_Enter_PreOperational:
        if ( d->nodeState == Operational || 
	     d->nodeState == Stopped )
	  setState(d,Pre_operational);
        break;
        
      case NMT_Reset_Node:
          setState(d,Initialisation);
        break;
        
      case NMT_Reset_Comunication:
          setState(d,Initialisation);
        break;
        
      }/* end switch */
      
    }/* end if( ( (*m).data[1] == 0 ) || ( (*m).data[1] == bDeviceNodeId ) ) */
  }
}


/*****************************************************************************/
UNS8 slaveSendBootUp(CO_Data* d)
{
  Message m;
	
  MSG_WAR(0x3407, "Send a Boot-Up msg ", 0);
	
  /* message configuration */
  m.cob_id.w = NODE_GUARD << 7 | *d->bDeviceNodeId;
  m.rtr = NOT_A_REQUEST;
  m.len = 1;
  m.data[0] = 0x00;
    
  return canSend(d->canHandle,&m);
}

