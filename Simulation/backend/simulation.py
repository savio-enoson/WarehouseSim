import pickle
from classes import *

if __name__ == '__main__':
    new_dataset = False     # 'True' 'False'
    queue_type = 'central'  # 'distributed' 'central'
    use_pq_main = True

    if new_dataset:
        volume = 100  # N of deliveries
        daily_ticks = 24 * 60  # Minutes in a day
        peaks = [5, 20]  # Peak times
        weights = [2, 1]  # Weights for each peak
        x = np.linspace(0, 23, daily_ticks)

        truck_classes = {
            "size": {
                "names": ['S', 'M', 'L', 'XL'],
                "probs": [0.2, 0.3, 0.4, 0.1],
                "dist": [
                    None,
                    None,
                    bimodal_distribution(x, 0.4, [13], [1]),
                    bimodal_distribution(x, 0.1, [1, 21], [1, 2]),
                ],
                "modifier": [1.5, 1.25, 1, 1],
            },
            "distance": {
                "names": ['Dekat', 'Sedang', 'Jauh'],
                "probs": [0.3, 0.4, 0.3],
                "dist": [
                    bimodal_distribution(x, 0.3, [8, 15], [1, 2]),
                    None,
                    bimodal_distribution(x, 0.3, [1, 21], [1, 2]),
                ],
                "modifier": [0.75, 1, 1.25],
            },
            "value": {
                "names": ['Low', 'Medium', 'High'],
                "probs": [0.6, 0.3, 0.1],
                "dist": None,
                "modifier": [0.75, 1, 2],
            },
            "shelf_life": {
                "names": ['Short', 'Long'],
                "probs": [0.15, 0.85],
                "dist": None,
                "modifier": [3, 1],
            },
        }

        dataset = Arrival(volume, peaks, weights, truck_classes)
        dataset.spawn_trucks()

        with open('dataset.pickle', 'wb') as handle:
            pickle.dump(dataset, handle, protocol=pickle.HIGHEST_PROTOCOL)
    else:
        try:
            with open('dataset.pickle', 'rb') as file:
                dataset = pickle.load(file)
        except:
            print("Error Loading Dataset!")
            exit()

    arrivals = dataset.arrivals

    # for i in arrivals:
    #     print(f"Tick :\t {i['tick']}\n{i['truck']}\n")
    # exit()

    # FUNCTION TO GRAPH TRUCK SPAWNING
    # dataset.plot_and_view()

    buffer = f"\tSpawned {len(arrivals)} Trucks"

    warehouses = [
        Warehouse({}, [
            Dock(55, 26, {}),
            Dock(50, 30, {}),
            Dock(52, 32, {}),
            Dock(52, 32, {})
        ], True, 5),
        Warehouse({}, [
            Dock(55, 26, {}),
            Dock(50, 30, {}),
            Dock(52, 32, {}),
            Dock(52, 32, {})
        ], True, 5),
    ]

    queue_length = 0
    FINISHED, PROCESSING, MISSED = [], [], []
    counter1, counter2 = 1, 1

    if queue_type == 'central':
        queue = SimulationQueue(use_pq_main)

        # RUN SIMULATION FOR 24 * 60 TICKS
        for clock in range(0, 1440):
            try:
                if clock == arrivals[0]['tick']:
                    queue.enqueue(arrivals.pop(0)['truck'])
            except:
                pass
            queue_length += len(queue.items)
            queue.tick(warehouses, clock)

        print("SERVER UTILIZATION (ρ)========================================")
        for wh in warehouses:
            print(f"Warehouse {counter1}")
            for dock in wh.loading_docks:
                print(
                    f"\tDock {counter2} Utilization: {dock.utilization_time} mins / {int((dock.utilization_time / 1440) * 100)}%")
                counter2 += 1
                if dock.occupied:
                    PROCESSING.append(dock.truck)
                FINISHED.extend(dock.served_trucks)
            counter1 += 1
            counter2 = 1
        MISSED = queue.items

        print("\n\nSUMMARY========================================")
        print(buffer)
        print(f"\tServed {len(FINISHED)} Trucks")
        print(f"\t{len(PROCESSING)} Trucks in Dock")
        print(f"\tMissed {len(MISSED)} Trucks")

        Lq = queue_length / 1440
        Wq, Wd = 0, 0

        FINISHED.extend(PROCESSING)
        for truck in FINISHED:
            Wq += truck.time_in_queue
            Wd += truck.time_at_dock
        Wq /= len(FINISHED)
        Wd /= len(FINISHED)

        print("\n\nQUEUE STATISTICS========================================")
        print(f"\tAVG Time in Queue (Wq)\t= {Wq:.2f} mins")
        print(f"\tAVG Time at Dock (Wd)\t= {Wd:.2f} mins")
        print(f"\tAVG Time in System (W)\t= {Wd + Wq:.2f} mins")
        print(f"\tAVG Queue Length (Lq)\t= {Lq:.2f}")

    elif queue_type == 'distributed':
        # Initialize main queue (trucks coming in) and warehouse queues
        WAITING = SimulationQueue(priority_queue=use_pq_main, control=False)
        for wh in warehouses:
            wh.queue = SimulationQueue(wh.priority_queue, wh.capacity)

        # RUN SIMULATION FOR 24 * 60 TICKS
        for clock in range(0, 1440):
            try:
                if clock == arrivals[0]['tick']:
                    WAITING.enqueue(arrivals.pop(0)['truck'])
            except:
                continue

            queue_length += len(WAITING.items)
            WAITING.tick(warehouses, clock)
            for wh in warehouses:
                wh.tick(clock)

        print("SERVER UTILIZATION (ρ)========================================")
        MISSED = WAITING.items
        for wh in warehouses:
            WAITING.items.extend(wh.queue.items)
            print(f"Warehouse {counter1} \tAVG Queue Len (Lq): {wh.queue_len/1440:.2f}")
            for dock in wh.loading_docks:
                print(
                    f"\tDock {counter2} Utilization: {dock.utilization_time} mins / {int((dock.utilization_time / 1440) * 100)}%")
                counter2 += 1
                if dock.occupied:
                    PROCESSING.append(dock.truck)
                FINISHED.extend(dock.served_trucks)
            counter1 += 1
            counter2 = 1

        print("\n\nSUMMARY========================================")
        print(buffer)
        print(f"\tServed {len(FINISHED)} Trucks")
        print(f"\t{len(PROCESSING)} Trucks in Dock")
        print(f"\tMissed {len(MISSED)} Trucks")

        LMq = queue_length / 1440
        LWq = 0
        for wh in warehouses:
            LWq += (wh.queue_len) / 1440
        LWq /= len(warehouses)

        Wq, Wd = 0, 0

        FINISHED.extend(PROCESSING)
        for truck in FINISHED:
            Wq += truck.time_in_queue
            Wd += truck.time_at_dock
        Wq /= len(FINISHED)
        Wd /= len(FINISHED)

        print("\n\nQUEUE STATISTICS========================================")
        print(f"\tAVG Time in Queue (Wq)\t= {Wq:.2f} mins")
        print(f"\tAVG Time at Dock (Wd)\t= {Wd:.2f} mins")
        print(f"\tAVG Time in System (W)\t= {Wd + Wq:.2f} mins")
        print(f"\tAVG Main Queue Length (LMq)\t\t= {LMq:.2f}")
        print(f"\tAVG Warehouse Queue Length (LWq)\t= {LWq:.2f}")

        # for i in FINISHED:
        #     print(i)