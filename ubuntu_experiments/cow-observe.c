/* Optional private-mapping/fork observation. Distinct visible values demonstrate
 * isolation; output alone does not prove which physical frame was copied. */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <sys/wait.h>
#include <unistd.h>
int main(void){
    long size=sysconf(_SC_PAGESIZE);if(size<=0)return 1;
    volatile unsigned char *p=mmap(NULL,(size_t)size,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
    if(p==MAP_FAILED){perror("mmap");return 1;}p[0]=7;
    int fd[2];if(pipe(fd)){perror("pipe");return 1;}fflush(NULL);pid_t child=fork();
    if(child<0){perror("fork");return 1;}
    if(child==0){close(fd[0]);p[0]=9;unsigned char value=p[0];ssize_t n=write(fd[1],&value,1);close(fd[1]);_exit(n==1?0:1);}
    close(fd[1]);unsigned char value=0;ssize_t n=read(fd[0],&value,1);close(fd[0]);int status;
    if(waitpid(child,&status,0)<0 || n!=1 || !WIFEXITED(status) || WEXITSTATUS(status)!=0){fputs("Child observation failed\n",stderr);return 1;}
    printf("child_private_value=%u parent_private_value=%u\n",(unsigned)value,(unsigned)p[0]);
    int ok=(value==9 && p[0]==7);munmap((void*)p,(size_t)size);return ok?0:1;
}
