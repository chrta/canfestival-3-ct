#include <stdlib.h>

#include <sys/time.h>
#include <pthread.h> 
#include <signal.h>

#include "applicfg.h"
#include "timer.h"

pthread_mutex_t CanFestival_mutex = PTHREAD_MUTEX_INITIALIZER;

TASK_HANDLE TimerLoopThread;

TIMEVAL last_time_set = TIMEVAL_MAX;

struct timeval last_sig;

timer_t timer;

void EnterMutex(void)
{
	pthread_mutex_lock(&CanFestival_mutex); 
}

void LeaveMutex(void)
{
	pthread_mutex_unlock(&CanFestival_mutex);
}

void timer_notify(sigval_t val)
{
	gettimeofday(&last_sig,NULL);
	EnterMutex();
	TimeDispatch();
	LeaveMutex();
//	printf("getCurrentTime() return=%u\n", p.tv_usec);
}

void initTimer(void)
{
	struct sigevent sigev;

	// Take first absolute time ref.
	gettimeofday(&last_sig,NULL);

	memset (&sigev, 0, sizeof (struct sigevent));
	sigev.sigev_value.sival_int = 0;
	sigev.sigev_notify = SIGEV_THREAD;
	sigev.sigev_notify_attributes = NULL;
	sigev.sigev_notify_function = timer_notify;

	timer_create (CLOCK_REALTIME, &sigev, &timer);
}

void StopTimerLoop(void)
{
	EnterMutex();
	timer_delete (timer);
	LeaveMutex();
}

void StartTimerLoop(TimerCallback_t init_callback)
{
	initTimer();
	EnterMutex();
	// At first, TimeDispatch will call init_callback.
	SetAlarm(NULL, 0, init_callback, 0, 0);
	LeaveMutex();
}

void CreateReceiveTask(CAN_PORT port, TASK_HANDLE* Thread, void* ReceiveLoopPtr)
{
	pthread_create(Thread, NULL, ReceiveLoopPtr, (void*)port);
}

void WaitReceiveTaskEnd(TASK_HANDLE Thread)
{
	pthread_kill(Thread, SIGTERM);
	pthread_join(Thread, NULL);
}

#define maxval(a,b) ((a>b)?a:b)
void setTimer(TIMEVAL value)
{
//	printf("setTimer(TIMEVAL value=%d)\n", value);
	// TIMEVAL is us whereas setitimer wants ns...
	long tv_nsec = 1000 * (maxval(value,1)%1000000);
	time_t tv_sec = value/1000000;
	struct itimerspec timerValues;
	timerValues.it_value.tv_sec = tv_sec;
	timerValues.it_value.tv_nsec = tv_nsec;
	timerValues.it_interval.tv_sec = 0;
	timerValues.it_interval.tv_nsec = 0;

 	timer_settime (timer, 0, &timerValues, NULL);
}

TIMEVAL getElapsedTime(void)
{
	struct timeval p;
	gettimeofday(&p,NULL);
//	printf("getCurrentTime() return=%u\n", p.tv_usec);
	return (p.tv_sec - last_sig.tv_sec)* 1000000 + p.tv_usec - last_sig.tv_usec;
}
