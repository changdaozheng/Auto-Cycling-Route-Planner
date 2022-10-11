from flask import Flask, request
from math import radians, cos, sin, asin, sqrt
import requests
from waitress import serve
import networkx as nx
import polyline
import random
import osmnx 



app = Flask(__name__)

# helper functions and classes
class Node:
    def __init__(self, osmid, lat, lng, parent_osmid, distance, is_visited):
        self.osmid = osmid
        self.lat = lat
        self.lng = lng
        self.parent_osmid = parent_osmid
        self.d = distance  # current distance from source node
        self.is_visited = is_visited

#SG bike network file
sg_bike_graph = nx.read_gpickle("sg_bike.gpickle")
nodes_df, streets_df = osmnx.graph_to_gdfs(sg_bike_graph)
nodes_df = nodes_df.reset_index()



nodes_dict = {}
def map_nodes(point):
  osmid = point['osmid']
  lat = point['y']
  lng = point['x']
  nodes_dict[osmid] = Node(osmid, lat, lng, None, 0, False)
nodes_df.apply(map_nodes, axis=1)


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
  try:
    req_bod = request.json 
    starting_lat = float(req_bod['starting_lat'])
    starting_lng = float(req_bod['starting_lng'])
    target_dist = int(req_bod['target_dist'])
    

    starting_pt_df = nodes_df[(abs(nodes_df['y'] - starting_lat) <= 0.000300 ) & (abs(nodes_df['x'] - starting_lng) <= 0.000300 )]
    
    if len(starting_pt_df) == 0:
        return "No routes nearby, try another point!", 404
    #Change starting to point to one of the nearest point on the graph
    rand_start = random.randrange(len(starting_pt_df.index))
    starting_osmid = starting_pt_df.iloc[rand_start,0]
   

  
    starting_node = nodes_dict[starting_osmid]
    stack = [starting_node]
    
    dist_flag = False
    while (len(stack) != 0):
      current_node = stack.pop()
      neighbours = get_neighbours(current_node.osmid)
      if (len(neighbours.index) == 1): 
          continue 

      for n in range(len(neighbours.index)):
        osmid = neighbours.iloc[n,0]
        neighbour = nodes_dict[osmid]

        if (osmid == current_node.osmid) or (osmid == starting_node.osmid) or (neighbour.is_visited == True): 
            continue
        else: 
            dist = current_node.d + haversine(current_node.lat, current_node.lng, neighbour.lat, neighbour.lng)

            neighbour.parent_osmid = current_node.osmid
            neighbour.d = dist
            neighbour.is_visited = True
            stack.append(neighbour)
        
            if dist > target_dist:
                dist_flag = True
                break      
      
      
      if dist_flag:
        arr = []     
        backtrack = neighbour
        counter = 0
        while(backtrack.parent_osmid != None):
            coords = [backtrack.lat,  backtrack.lng]
            arr.append(coords)
            
            counter +=1
            backtrack = nodes_dict[backtrack.parent_osmid]
        
        route_geom = polyline.encode(arr)

        start = arr[0]
        end = arr[-1]
        start_pt = requests.post("https://SWE-Backend.chayhuixiang.repl.co/geocode", json={"lat": start[0], "lng": start[1]}).json()['address']
        end_pt = requests.post("https://SWE-Backend.chayhuixiang.repl.co/geocode", json={"lat": end[0], "lng": end[1]}).json()['address']
        return {"route_geom":route_geom, "distance": dist, "start_pt": {"pt_address": start_pt, "lat": start[0], "lng": start[1]}, "end_pt": {"pt_address": end_pt, "lat": end[0], "lng": end[1]}}

  except Exception as e:
    return e, 500 
  

@app.route('/test', methods=['GET', 'POST'])
def test():
  return "API Healthy"

if __name__ == "__main__":
  serve(app, host="0.0.0.0", port=29810)
  