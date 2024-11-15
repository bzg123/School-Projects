import xml.dom.minidom
import random
from threading import Thread
# global memory sizes
main_mem = [None] * 32
virtual_mem = [None] * 32


# generates processes from the template file
def process_gen(tempfile):
    template = xml.dom.minidom.parse(tempfile)
    num_process = input("Enter number of processes: ")
    operations = template.getElementsByTagName("operation")
    pcb = [[['0' for _ in range(2)] for _ in range(operations.length + 1)] for _ in range(int(num_process))]

    for i in range(0, int(num_process)):
        # empty page table
        pcb[i][0][0] = [i, ['-']*operations.length]
        # process state
        pcb[i][0][1] = 'NEW'
        # operations based on template
        for j in range(1, operations.length + 1):
            pcb[i][j][0] = operations[j - 1].getAttribute("type")
            min_cycles = operations[j - 1].getElementsByTagName("min")[0].childNodes[0].data
            max_cycles = operations[j - 1].getElementsByTagName("max")[0].childNodes[0].data
            cycle_length = random.randint(int(min_cycles), int(max_cycles))
            pcb[i][j][1] = cycle_length
    return pcb


# Checks if processes are able to go to the ready state
def ready_check(pcb):
    n = 0
    for i in range(0, len(pcb)):
        p_check = True
        # adds process to memory if there's space
        if main_mem.count(None) >= (len(pcb[0]) - 1):
            for j in range(1, len(pcb[0])):
                # makes sure operations have the right name
                if (pcb[i][j][0] != 'CALCULATE'
                        and pcb[i][j][0] != 'I/O'
                        and pcb[i][j][0] != 'FORK'
                        and pcb[i][j][0] != 'CALCULATE(crit)'):
                    p_check = False
                main_mem[n] = (i, j-1)
                pcb[i][0][0][1][j-1] = n
                n += 1
        else:
            p_check = False
        if p_check:
            pcb[i][0][1] = 'READY'
    return pcb


# first come first serve scheduling
def fcfs(pcb):
    num_cycles = int(input("Enter number of cycles to run( or enter 0 to run to completion): "))
    if num_cycles == 0:
        num_cycles = 100000

    while not (pcb_complete(pcb)):
        # running ready process
        if pcb[0][0][1] == 'READY':
            for j in range(1, len(pcb[0])):
                if pcb[0][j][0] == 'CALCULATE' or pcb[0][j][0] == 'CALCULATE(crit)':
                    if pcb[0][j][1] > 0:
                        pcb[0][0][1] = 'RUN(T0)'
                        # find processes that can be run in parallel
                        readied = []
                        for i in range(1, len(pcb)):
                            if pcb[i][0][1] == 'READY':
                                for k in range(1, len(pcb[0])):
                                    if pcb[i][k][0] == 'CALCULATE(crit)':
                                        if pcb[i][k][1] > 0:
                                            break
                                    if pcb[i][k][0] == 'CALCULATE':
                                        if pcb[i][k][1] > 0:
                                            readied.append((i,k))
                                            break
                        # changes state to run and on which thread
                        if len(readied) > 2:
                            pcb[readied[0][0]][0][1] = 'RUN(T1)'
                            pcb[readied[1][0]][0][1] = 'RUN(T2)'
                            pcb[readied[2][0]][0][1] = 'RUN(T3)'
                        while pcb[0][j][1] > 0:
                            # decrementing the threads of the different processes
                            pcb[0][j][1] -= 1
                            if len(readied) > 2:
                                if pcb[readied[0][0]][readied[0][1]][1] > 0:
                                    pcb[readied[0][0]][readied[0][1]][1] -= 1
                                if pcb[readied[1][0]][readied[1][1]][1] > 0:
                                    pcb[readied[1][0]][readied[1][1]][1] -= 1
                                if pcb[readied[2][0]][readied[2][1]][1] > 0:
                                    pcb[readied[2][0]][readied[2][1]][1] -= 1
                            # decrementing waiting processes
                            pcb = cycle_wait(pcb)
                            num_cycles -= 1
                            # breaking when user specified
                            if num_cycles == 0:
                                return pcb, 'Incomplete', num_cycles
                        # change extra threads back to ready
                        if len(readied) > 2:
                            pcb[readied[0][0]][0][1] = 'READY'
                            pcb[readied[1][0]][0][1] = 'READY'
                            pcb[readied[2][0]][0][1] = 'READY'
                elif pcb[0][j][0] == 'I/O':
                    if pcb[0][j][1] > 0:
                        pcb[0][0][1] = 'WAIT'
                        pcb.append(pcb.pop(0))
                        break
                # updating page table and memory
                pcb = page_table_update(pcb, 0, j)
            if pcb[0][0][1] == 'RUN(T0)':
                pcb[0][0][1] = 'EXIT'
        # Waiting for I/O
        elif pcb[0][0][1] == 'WAIT':
            for i in range(1, len(pcb[0])):
                if pcb[0][i][0] == 'I/O':
                    while pcb[0][i][1] > 0:
                        pcb[0][i][1] -= 1
                        pcb = cycle_wait(pcb)
                        num_cycles -= 1
                        if num_cycles == 0:
                            return pcb, 'Incomplete', num_cycles
                elif pcb[0][i][0] == 'CALCULATE' or pcb[0][i][0] == 'CALCULATE(crit)':
                    if pcb[0][i][1] > 0:
                        pcb[0][0][1] = 'READY'
                        break
                pcb = page_table_update(pcb, 0, i)
            # process set to exit
            if pcb[0][0][1] == 'WAIT':
                pcb[0][0][1] = 'EXIT'
                pcb.append(pcb.pop(0))
        elif pcb[0][0][1] == 'EXIT':
            # keeps loop going
            pcb.append(pcb.pop(0))
        elif pcb[0][0][1] == 'NEW':
            # gets a new process ready when there's space in memory
            if main_mem.count(None) >= len(pcb[0]) - 1:
                empty_spots = []
                for i in range(0, len(main_mem)):
                    if main_mem[i] is None:
                        empty_spots.append(i)
                for j in range(0, len(pcb[0]) - 1):
                    main_mem[empty_spots[j]] = (pcb[0][0][0][0], j)
                    pcb[0][0][0][1][j] = empty_spots[j]
                pcb[0][0][1] = 'READY'
            else:
                pcb.append(pcb.pop(0))
    pcb = clean_pcb(pcb)

    return pcb, 'Completed', num_cycles


# Checks if all the process have run to completion
def pcb_complete(pcb):
    completed = True
    for i in range(0, len(pcb)):
        if pcb[i][0][1] != 'EXIT':
            completed = False
    return completed


# decrements all waiting processes when a cycle happens
def cycle_wait(pcb):
    for i in range(1, len(pcb)):
        if pcb[i][0][1] == 'WAIT':
            for j in range(1, len(pcb[0])):
                if pcb[i][j][0] == 'I/O':
                    if pcb[i][j][1] > 0:
                        pcb[i][j][1] -= 1
                        break
                elif pcb[i][j][0] == 'CALCULATE' or pcb[i][j][0] == 'CALCULATE(crit)':
                    if pcb[i][j][1] > 0:
                        pcb[i][0][1] = 'READY'
                        break
                pcb = page_table_update(pcb, i, j)
    return pcb


# keeps page table and memory up to date as process are running
def page_table_update(pcb, i, j):
    if pcb[i][j][1] == 0:
        for k in range(0, len(main_mem)):
            # swapping operations to virtual memory
            if main_mem[k] is not None:
                if main_mem[k][0] == pcb[i][0][0][0] and main_mem[k][1] == j - 1:
                    if virtual_mem[k] is not None:
                        for m in range(0, len(pcb)):
                            if pcb[m][0][0][0] == virtual_mem[k][0]:
                                pcb[m][0][0][1][virtual_mem[k][1]] = '-'
                        virtual_mem[k] = main_mem[k]
                    else:
                        virtual_mem[k] = main_mem[k]
                    main_mem[k] = None
                    pcb[i][0][0][1][j - 1] = k + len(main_mem)
    # adds new processes
    for k in range(1, len(pcb)):
        if pcb[k][0][1] == 'NEW':
            # check if enough space in memory for new process
            if main_mem.count(None) >= len(pcb[0]) - 1:
                empty_spots = []
                # updates page table and memory
                for n in range(0, len(main_mem)):
                    if main_mem[n] is None:
                        empty_spots.append(n)
                for m in range(0, len(pcb[0])-1):
                    main_mem[empty_spots[m]] = (pcb[k][0][0][0], m)
                    pcb[k][0][0][1][m] = empty_spots[m]
                pcb[k][0][1] = 'READY'
                break
    return pcb


# removes operations from memory when complete
def clean_pcb(pcb):
    for i in range(0, len(virtual_mem)):
        virtual_mem[i] = None
    for j in range(0, len(pcb)):
        for k in range(0, len(pcb[j])):
            pcb[j][0][0][1][k-1] = '-'
    return pcb


def main():
    pcb = process_gen('template.xml')
    print('Generated processes:')
    for i in range(len(pcb)):
        print(pcb[i])
    # better printing
    print()
    pcb = ready_check(pcb)
    pcb, status, cycles = fcfs(pcb)
    print('Current state of processes:')
    mid = len(pcb) // 2
    cpu1 = pcb[:mid]
    cpu2 = pcb[mid:]
    print('CPU 1:')
    for i in range(len(cpu1)):
        print(cpu1[i])
    print('CPU 2:')
    for i in range(len(cpu2)):
        print(cpu2[i])
    print('Status of the program: ', status)
    if cycles != 0:
        print('Number of cycles ran:', 100000 - cycles)
    print("Current state of main memory:")
    print(main_mem)
    print("Current state of virtual memory:")
    print(virtual_mem)


if __name__ == "__main__":
    main()
