/*
This file is part of CanFestival, a library implementing CanOpen Stack.

Copyright (C): Edouard TISSERANT and Francis DUPIN
Win32 Port Leonid Tochinski

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
#ifndef CANFESTIVAL_H_
#define CANFESTIVAL_H_

#include "timerscfg.h"
#include "can_driver.h"
#include "data.h"
#include "timers_driver.h"

#include <windows.h>
typedef HINSTANCE LIB_HANDLE;

UNS8 UnLoadCanDriver(LIB_HANDLE handle);
LIB_HANDLE LoadCanDriver(LPCSTR driver_name);
UNS8 canSend(CAN_PORT port, Message *m);
CAN_PORT canOpen(s_BOARD *board, CO_Data * d);
int canClose(CO_Data * d);
UNS8 canChangeBaudRate(CAN_PORT port, char* baud);

#endif /*CANFESTIVAL_H_*/
