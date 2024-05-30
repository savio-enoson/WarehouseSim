import math
import random
import numpy as np
from matplotlib import pyplot as plt
from functions import map_size, bimodal_distribution, get_class


class SimulationQueue:
    def __init__(self, priority_queue=False, capacity=9999, control=True):
        self.items = []
        self.capacity = capacity
        self.priority_queue = priority_queue
        self.control = control

    def __str__(self):
        buffer = ""
        for i in self.items:
            buffer += str(i) + "\n"
        return f"{len(self.items)}/{self.capacity}\n{buffer}"

    def enqueue(self, item):
        self.items.append(item)

    def tick(self, warehouses, clock):
        # Take the highest priority score without changing the order of the queue.
        try:
            front_most = sorted(self.items, key=lambda x: x.priority_score + (x.time_in_queue/10), reverse=True)[0] \
                if self.priority_queue else self.items[0]
        except:
            front_most = None

        # The control queue calls the tick method for all children (warehouses and docks).
        if self.control:
            # Check front most truck's compatibility with each warehouse
            if front_most:
                processed = False
                for wh in warehouses:
                    if wh.is_compatible(front_most):
                        # If a warehouse is compatible, proceed to check each dock
                        for dock in wh.loading_docks:
                            if dock.is_compatible(front_most):
                                dock.process_truck(front_most, clock)
                                self.items.remove(front_most)
                                processed = True
                                break
                    if processed:
                        break

            for i in self.items:
                i.time_in_queue += 1
            for wh in warehouses:
                wh.tick(clock)
        else:
            # If the queue does not control ticks, it should only append the front most truck to compatible warehouses
            # (distributed architecture), and progress the waiting times of each member inside it.
            if front_most:
                processed = False
                for wh in warehouses:
                    if wh.is_compatible(front_most):
                        # If a warehouse is compatible, enqueue the truck.
                        wh.queue.enqueue(front_most)
                        self.items.remove(front_most)
                        processed = True

                    if processed:
                        break

            for i in self.items:
                i.time_in_queue += 1


class Truck:
    def __init__(self, params, load, score):
        self.size = params['size']
        self.vol, self.weight = map_size(self.size, load)
        self.priority_score = score
        self.params = params

        self.time_in_queue = 0
        self.time_at_dock = 0

    def __str__(self):
        return (f"Parameters: {self.params}\n"
                f"Vol: {self.vol:.3f}\t Weight: {self.weight:.3f}\t Score: {self.priority_score:.2f}\n"
                f"In Queue: {self.time_in_queue:.2f} mins\t At Dock: {self.time_at_dock:.2f} mins")


class Warehouse:
    def __init__(self, restrictions, loading_docks=None, priority_queue=False, capacity=9999):
        if loading_docks is None:
            loading_docks = []
        self.loading_docks = loading_docks
        self.restrictions = restrictions
        self.queue = None
        self.queue_len = 0
        self.priority_queue = priority_queue
        self.capacity = capacity

    def __str__(self):
        ld_status = ''
        for i in self.loading_docks:
            ld_status += str(i)
        return f"Warehouse Rules: {str(self.restrictions)}\n{ld_status}"

    def tick(self, clock):
        # Process internal queue, should user pick the multiple M/G/c queue setting
        if self.queue:
            QUEUE = self.queue
            self.queue_len += len(QUEUE.items)
            try:
                front_most = sorted(QUEUE.items, key=lambda x: x.priority_score + (x.time_in_queue/10), reverse=True)[0] \
                    if QUEUE.priority_queue else QUEUE.items[0]
            except:
                front_most = None

            if front_most:
                processed = False
                for dock in self.loading_docks:
                    if dock.is_compatible(front_most):
                        dock.process_truck(front_most, clock)
                        QUEUE.items.remove(front_most)
                        processed = True
                        break
                    if processed:
                        break

                for i in QUEUE.items:
                    i.time_in_queue += 1

        for i in self.loading_docks:
            i.tick(clock)

    def is_compatible(self, truck):
        if self.queue and (len(self.queue.items) >= self.queue.capacity):
            return False
        if not self.restrictions:
            return True

        for key, value in truck.params.items():
            try:
                if value in self.restrictions[key]:
                    continue
                else:
                    return False
            except:
                continue
        return True

    def create_LD(self, vol_capacity, weight_capacity, params):
        self.loading_docks.append(Dock(vol_capacity, weight_capacity, params))


class Dock:
    def __init__(self, vol_capacity, weight_capacity, restrictions):
        self.occupied = False
        self.truck = None
        self.use_start = None
        self.use_finish = None
        self.served_trucks = []

        self.vol_capacity = vol_capacity
        self.weight_capacity = weight_capacity
        self.restrictions = restrictions

        self.utilization_time = 0

    def __str__(self):
        return (f"Status: {'Occupied' if self.occupied else 'Free'}\tCapacity: {self.vol_capacity}|"
                f"{self.weight_capacity}/tick\tRules: {str(self.restrictions)}\n")

    def is_compatible(self, truck):
        if self.occupied:
            return False
        if not self.restrictions:
            return True
        for key, value in truck.params.items():
            try:
                if value in self.restrictions[key]:
                    continue
                else:
                    return False
            except:
                continue
        return True

    def tick(self, clock):
        if self.occupied:
            if clock == self.use_finish:
                self.served_trucks.append(self.truck)
                self.occupied = False
                self.truck = None
                self.use_start = None
                self.use_finish = None
            else:
                self.truck.time_at_dock += 1

            self.utilization_time += 1

    def process_truck(self, truck, clock):
        self.occupied = True
        self.use_start = clock
        self.truck = truck

        # Lowest processing time between volume and weight is taken
        if truck.vol / self.vol_capacity <= truck.weight / self.weight_capacity:
            self.use_finish = clock + math.ceil(truck.vol / self.vol_capacity)
        else:
            self.use_finish = clock + math.ceil(truck.weight / self.weight_capacity)


class Arrival:
    def __init__(self, volume, peaks, weights, truck_classes):
        self.volume = volume
        self.peaks = peaks
        self.weights = weights
        self.truck_classes = truck_classes

        self.daily_ticks = 60 * 24
        self.x = np.linspace(0, 23, self.daily_ticks)  # Generate n discrete axes
        self.arrivals = []
        self.y = bimodal_distribution(self.x, (volume / self.daily_ticks), peaks, weights)

    def spawn_trucks(self):
        if len(self.arrivals) == 0:
            arrivals = []

            # For each tick, roll a die to see if it spawns a truck
            for i in range(len(self.y)):
                rng = random.random()

                # If a truck is spawned, randomize its parameters.
                if rng <= self.y[i]:
                    params = {}
                    score = 10
                    for key, value in self.truck_classes.items():
                        if value['dist']:
                            buffer = []
                            for j in range(0, len(value['dist'])):
                                f_dist = value['dist'][j]
                                if f_dist is not None:
                                    buffer.append(f_dist[j])
                                else:
                                    buffer.append(value['probs'][j])

                            sum_prob = sum(buffer)
                            normalized_probs = list(map(lambda x: x / sum_prob, buffer))
                            params[key] = get_class(value['names'], normalized_probs, random.random())
                        else:
                            params[key] = get_class(value['names'], value['probs'], random.random())

                        score *= value['modifier'][value['names'].index(params[key])]

                    load = 0.6 + (random.random() * 0.4)
                    arrivals.append({
                        'tick': i,
                        'time': self.x[i],
                        'truck': Truck(params, load, score)
                    })

            # The result is often too high. Now scale to the average number of arrivals
            scaling_factor = self.volume / len(arrivals)
            arrivals = [x for x in arrivals if random.random() <= scaling_factor]  # Trim to scaling factor
            self.arrivals = arrivals
        return self.arrivals

    def plot_and_view(self):
        plt.figure(figsize=(5, 5))
        plt.subplot(2, 1, 1)
        plt.plot(self.x, self.y, label='Arrivals', color='red')
        plt.xlabel('Time')
        plt.ylabel('Arrival Probability')
        plt.title('Arrival Distribution Function')
        plt.legend()

        arrival_y = [0] * 24
        arrival_x = np.linspace(0, 23, 24)

        for i in self.arrivals:
            arrival_y[int(i.get('time')) - 1] += 1

        # for i in range(len(arrival_y)):
        #     print(f"{arrival_y[i]} Trucks arrived at {i}")

        # View Arrivals
        plt.subplot(2, 1, 2)
        plt.plot(arrival_x, arrival_y, label=f'Arrivals ({sum(arrival_y)})', color='blue')
        plt.xlabel('Time')
        plt.ylabel('Number of Trucks')
        plt.title('Arrival Rate')
        plt.legend()

        plt.tight_layout()
        plt.subplots_adjust(top=0.9, left=0.1)
        plt.show()
