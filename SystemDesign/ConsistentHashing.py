import random
from collections import defaultdict
import math


user_ids = ["user"+str(x) for x in range(100)]
no_of_nodes = 10

user_server_map = defaultdict(set)
server_list = [""]*1000

# map servers to a range of 100
for i in range(no_of_nodes):
    random.seed(i)
    server_list[random.randint(0, 999)] = "server"+str(i)
    server_list[random.randint(0, 999)] = "server"+str(i)
    server_list[random.randint(0, 999)] = "server"+str(i)
    server_list[random.randint(0, 999)] = "server"+str(i)
    server_list[random.randint(0, 999)] = "server"+str(i)


# print(server_list)

# assuming every user sends 1000 requests
for _ in range(100):
    for i in range(100):
        random.seed(user_ids[i])
        orig_pick = random.randint(0, 999)
        pick = orig_pick
        while pick < orig_pick and pick < len(server_list):
            while server_list[pick] == "" and pick < len(server_list):
                pick += 1
            if pick == len(server_list):
                pick = 0
        if server_list[pick] != "":
            user_server_map[user_ids[i]].add(server_list[orig_pick])
        else:
            # unexpected case
            continue


# print all users associated with server1
server1_users = []
for k, v in user_server_map.items():
    if "server1" in v:
        server1_users.append(k)
        print(k, v)

# remove server1 entries in server_list and replace with ""
server_list = ["" if x == "server1" else x for x in server_list]
# print(server_list)
user_server_map2 = defaultdict(set)

# send another 1000 request
for _ in range(100):
    for i in range(100):
        random.seed(user_ids[i])
        orig_pick = random.randint(0, 999)
        pick = orig_pick
        while server_list[pick] == "" and pick < len(server_list):
            pick += 1
            if pick == len(server_list):
                pick = 0
            elif pick == orig_pick:
                break
        if server_list[pick] != "":
            user_server_map2[user_ids[i]].add(server_list[pick])
        else:
            # unexpected case
            continue


# print users in server1_users and their servers
for user in server1_users:
    print(user, user_server_map2[user])

