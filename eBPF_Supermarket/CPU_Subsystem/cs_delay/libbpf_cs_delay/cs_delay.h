#ifndef __CS_DELAY_H
#define __CS_DELAY_H

struct event {
	pid_t pid;
	long unsigned int t1;
	long unsigned int t2;
	long unsigned int delay;
};

#endif /* __CS_DELAY_H */
