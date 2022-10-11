from gevent import monkey
monkey.patch_all()


from flask import Flask, request
from math import radians, cos, sin, asin, sqrt
from gevent.pywsgi import WSGIServer
from flask_compress import Compress
import networkx as nx
import polyline
import random
import osmnx 



app = Flask(__name__)
compress = Compress()
compress.init_app(app)

#SG bike network file
sg_bike_graph = nx.read_gpickle("sg_bike.gpickle")

# helper functions and classes
class Node:
    def __init__(self, osmid, lat, lng, parent_osmid, distance):
        self.osmid = osmid
        self.lat = lat
        self.lng = lng
        self.parent_osmid = parent_osmid
        self.d = distance  # current distance from source node

def get_neighbours(osmid):  
    ego = nx.ego_graph(sg_bike_graph, osmid, radius=1, center=True, undirected=False, distance=None)
    n, s = osmnx.graph_to_gdfs(ego)
    n = n.reset_index()
    return n


def haversine(lat1, lon1, lat2, lon2):

      R = 6372.8 # this is in miles.  For Earth radius in kilometers use 6372.8 km

      dLat = radians(lat2 - lat1)
      dLon = radians(lon2 - lon1)
      lat1 = radians(lat1)
      lat2 = radians(lat2)

      a = sin(dLat/2)**2 + cos(lat1)*cos(lat2)*sin(dLon/2)**2
      c = 2*asin(sqrt(a))

      return R * c


@app.route('/imfeelinglucky', methods = ['POST'])
def route_plot():
  req_bod = request.json 
  starting_osmid = int(req_bod['starting_osmid'])
  starting_lat = float(req_bod['starting_lat'])
  starting_lng = float(req_bod['starting_lng'])
  target_dist = int(req_bod['target_dist'])

  starting_node = Node(starting_osmid, starting_lat, starting_lng, None, 0)
  stack = [starting_node]
  nodes_dict = {starting_osmid: starting_node}
  
  dist_flag = False
  while (len(stack) != 0):
    current_node = stack.pop()
    neighbours = get_neighbours(current_node.osmid)
    if (len(neighbours.index) == 1): 
        continue
    else:
        nodes_dict[current_node.osmid] = current_node

    counter_arr = []
    for i in range(len(neighbours.index)):
      counter_arr.append(i)

    for i in range(len(neighbours.index)):
      n = counter_arr[random.randrange(len(counter_arr))]

      osmid = neighbours.iloc[n,0]
      if (osmid == current_node.osmid) or (osmid == starting_node.osmid) : continue
      lat = neighbours.iloc[n,1]
      lng = neighbours.iloc[n,2]
      dist = current_node.d + haversine(current_node.lat, current_node.lng, lat, lng)

      neighbour_node = Node(osmid, lat, lng, current_node.osmid, dist)

      stack.append(neighbour_node)
      
      if dist > target_dist:
        dist_flag = True

      counter_arr.remove(n)
    
    
    
    if dist_flag:
        arr = []
        for key in nodes_dict.keys():
            cur_node = nodes_dict[key]
            coords = [cur_node.lat,  cur_node.lng]
            arr.append(coords)
        route_geom = polyline.encode(arr)
        print(route_geom)
        return {"route_geom":route_geom, "distance": dist}

if __name__ == "__main__":
    http_server = WSGIServer(('0.0.0.0', 8080), app)
    http_server.serve_forever()