/* Optional bounded observation. Use a fresh process; counters include runtime noise.
 * An anonymous mapping is not the same as a file read. No exact fault count promised.
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <sys/resource.h>
#include <unistd.h>
static struct rusage snapshot(void){struct rusage r;if(getrusage(RUSAGE_SELF,&r)){perror("getrusage");exit(1);}return r;}
static void report(const char *label,struct rusage a,struct rusage b){printf("%-18s minor_delta=%ld major_delta=%ld\n",label,b.ru_minflt-a.ru_minflt,b.ru_majflt-a.ru_majflt);}
int main(void){
    long page=sysconf(_SC_PAGESIZE);if(page<=0){fputs("Page size unavailable\n",stderr);return 1;}
    const size_t bytes=16u*1024u*1024u;unsigned long checksum=0;
    printf("pid=%ld page_size=%ld mapping_bytes=%zu\n",(long)getpid(),page,bytes);fflush(stdout);
    struct rusage a=snapshot();
    volatile unsigned char *p=mmap(NULL,bytes,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);
    if(p==MAP_FAILED){perror("mmap");return 1;}struct rusage b=snapshot();
    for(size_t i=0;i<bytes;i+=(size_t)page)checksum+=p[i];struct rusage c=snapshot();
    for(size_t i=0;i<bytes;i+=(size_t)page)p[i]=1;struct rusage d=snapshot();
    for(size_t i=0;i<bytes;i+=(size_t)page)p[i]+=1;struct rusage e=snapshot();
    report("mapping only",a,b);report("first read",b,c);report("first write",c,d);report("repeat write",d,e);
    printf("checksum=%lu first_byte=%u\n",checksum,(unsigned)p[0]);
    if(munmap((void*)p,bytes)){perror("munmap");return 1;}return 0;
}
