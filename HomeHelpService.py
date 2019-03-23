from gurobipy import *
import numpy as np
import matplotlib.pyplot as plt
import math
import itertools
import random
import mysql.connector
import googlemaps
import gmplot

rnd = np.random
# rnd.seed(391761407)
# rnd.seed(3345479024) 
print("Seed was:", rnd.get_state()[1][0])
def makeRandomAssignments():
  n = 10
  e = 5
  v = n+e
  Q = n/e
  N = [i for i in range(n)]
  E = [i for i in range(n, n+e)]
  V = N+E

  print(v)
  print(V)

  loc_x = rnd.rand(len(V))*200
  loc_y = rnd.rand(len(V))*100
  print(loc_x)
  A = [(i,j) for i in V  for j in V if i != j]
  c = {(i,j):np.hypot(loc_x[i]-loc_x[j],loc_y[i]-loc_y[j]) for i,j in A}
  for i in N:
      plt.plot(loc_x[i], loc_y[i], c='b', marker='o')
      plt.annotate('c=%d'%(i),(loc_x[i]+2, loc_y[i]))
  for i in E:
      plt.plot(loc_x[i], loc_y[i], c='r', marker='s')
      plt.annotate('e=%d'%(i),(loc_x[i]+2, loc_y[i]))
  plt.axis('equal')

  #create model
  m = Model()

  # set variables
  x=m.addVars(A, vtype=GRB.BINARY, name='x')
  u=m.addVars(V, ub=Q, vtype=GRB.INTEGER, name='u')

  m.update()

  # #minimize problem 
  m.setObjective(quicksum(c[i,j]*x[i,j] for i,j in A), GRB.MINIMIZE)

  # #constraints
  con1_1 = m.addConstrs(quicksum(x[i,j] for j in V if j!=i)==1 for i in N)
  con1_2 = m.addConstrs(quicksum(x[i,j] for i in V if i!=j)==1 for j in V)
  con2_1 = m.addConstrs(quicksum(x[i,j] for j in V if j!=i)==1 for i in E)
  con2_2 = m.addConstrs(quicksum(x[i,j] for i in V if i!=j)==1 for j in E)

  con3 = m.addConstrs((x[i,j] == 1) >> (x[i,j] == 0) for i,j in A if i in E and j in E and i!=j)
  con9 = m.addConstrs((x[i,j] == 1) >> (u[i]-u[j]+(Q*x[i,j])==Q-1) for i,j in A if i not in E and j not in E and i!=j)
  # con6 = m.addConstrs(u[i]<=Q for i in N)
  # for i in N:
  #   m.addConstr(sum(x[i,j] for j in V if i!=j) == 2)

  def subtour(edges):
    visited = [False]*v
    cycles = []
    lengths = []
    selected = [[] for i in range(v)]
    for x,y in edges:
      selected[x].append(y)
    while True:
      current = visited.index(False)
      for i in range(v):
        if visited[i] == False:
          neighbors = [x for x in selected[i]]
          if len(neighbors) == 1:
            current = i
      thiscycle = [current]
      while True:
        visited[current] = True
        neighbors = [x for x in selected[current] if not visited[x]]
        if len(neighbors) == 0:
          break
        current = neighbors[0]
        thiscycle.append(current)
      cycles.append(thiscycle)
      lengths.append(len(thiscycle))
      if sum(lengths) == v:
        break
    return cycles

  def subtourelim(model, where):
    if where == GRB.callback.MIPSOL:
      selected = []
      # make a list of edges selected in the solution
      for i in V:
        for j in V:
          if (i != j):
            sol = model.cbGetSolution(x[i,j])
            if sol > 0.5:
              selected += [(i,j)]
      tours = subtour(selected)
      for t in tours:
        SUnion = []
        I = []
        for node in t:
          if node in N:
            SUnion.append(node)
          else: 
            I.append(node)
        S = SUnion[1:-1]
        if len(I) == 0 and len(t)>1:
          print('no empoloyees')
          model.cbLazy(quicksum(x[i,j] for i,j in itertools.combinations(t, 2))<= len(t)-1)
        elif len(I)>=2 and len(SUnion) == 1:
          model.cbLazy(x[I[0],SUnion[0]] + quicksum(x[i,SUnion[0]] for i in E if i!=I[0])<=1)
        elif len(S)>0 and len(I)>=2:
          print('more than 1 employee, more than 2 clients')
          model.cbLazy(x[I[0],SUnion[0]] + quicksum(x[i,j] for i in E for j in SUnion if i!=I[0])<=1)
        elif len(SUnion) == 2 and len(I)>=2:
          print('only 2 clients and 2 employees')
          model.cbLazy(x[I[0],SUnion[0]] + 3*x[SUnion[0],SUnion[1]] + quicksum(x[i,SUnion[1]] for i in E if i!=I[0])<= 4)    

  # Optimize
  m._vars = m.getVars()
  m.params.LazyConstraints = 1
  # m.params.Threads = 1
  m.params.Cuts = 0
  m.optimize(subtourelim)
  status = m.status

  if status == GRB.Status.UNBOUNDED:
      print('The model cannot be solved because it is unbounded')
      exit(0)
  if status == GRB.Status.OPTIMAL:
      print('The optimal objective is %g' % m.objVal)
      sol = m.getAttr('x', x)
      selected = [i for i in sol if sol[i] > 0.5]
      finalTour = subtour(selected)
      print('---------FINAL TOUR-----------')
      print(finalTour)
      print(selected)
      for i in selected:
          plt.plot((loc_x[i[0]],loc_x[i[1]]), (loc_y[i[0]],loc_y[i[1]]), color='r')
      plt.show()
      exit(0)
  if status != GRB.Status.INF_OR_UNBD and status != GRB.Status.INFEASIBLE:
      print('Optimization was stopped with status %d' % status)
      exit(0)

  print('The model is infeasible; relaxing the constraints')
  m.feasRelaxS(0, False, False, True)
  # m.feasRelaxS(2, False, False, True)
  # m.relax()
  m.optimize(subtourelim)
  status = m.status

  if status == GRB.Status.OPTIMAL:
      print('The optimal objective is %g' % m.objVal)
      sol = m.getAttr('x', x)
      selected = [i for i in sol if sol[i] > 0.5]
      finalTour = subtour(selected)
      print('---------FINAL TOUR-----------')
      print(finalTour)
      print(selected)
      for i in selected:
          plt.plot((loc_x[i[0]],loc_x[i[1]]), (loc_y[i[0]],loc_y[i[1]]), color='r')
      plt.show()
      exit(0)

  if status in (GRB.Status.INF_OR_UNBD, GRB.Status.INFEASIBLE, GRB.Status.UNBOUNDED):
      print('The relaxed model cannot be solved \
            because it is infeasible or unbounded')
      exit(1)

  if status != GRB.Status.OPTIMAL:
      print('Optimization was stopped with status %d' % status)
      exit(1)


def makeAssignments(N, E, locations):
  API_key = 'AIzaSyB9sCDlGCG0hnDydbCAXAko3ogG34C4-0w'#enter Google Maps API key
  gmaps = googlemaps.Client(key=API_key)

  n = len(N)
  e = len(E)
  v = n+e
  Q = n/e
  V = N+E
  A = [(i,j) for i in V for j in V if i != j]
  c = {(i,j): gmaps.distance_matrix(locations[i], locations[j], mode='walking')["rows"][0]["elements"][0]["distance"]["value"] for i,j in A}
  
  #place the map in the middle of Cardiff
  # gmap = gmplot.GoogleMapPlotter(51.481583, -3.179090, 13)

  # print(top_attraction_lats)
  # gmap.scatter(top_attraction_lats, top_attraction_lons, '#3B0B39', size=40, marker=False)
  # lat_long = []
  # for i in V:
  #  lat_long.append(locations[i])
  # top_attraction_lats, top_attraction_lons = zip(*lat_long)
  # gmap.scatter(top_attraction_lats, top_attraction_lons, '#3B0B39', size=40, marker=True)
  # gmap.draw("my_map.html")
  for i in N:
    plt.plot(locations[i][0], locations[i][1], c='b', marker='o')
    plt.annotate('c=%d'%(i),(locations[i][0], locations[i][1]))
  for i in E:
    print(locations[i][0])
    plt.plot(locations[i][0], locations[i][1], c='r', marker='s')
    plt.annotate('e=%d'%(i),(locations[i][0], locations[i][1]))
  plt.axis('equal')
  #create model
  m = Model()

  # set variables
  x=m.addVars(A, vtype=GRB.BINARY, name='x')
  u=m.addVars(V, ub=Q, vtype=GRB.INTEGER, name='u')

  m.update()

  # #minimize problem 
  m.setObjective(quicksum(c[i,j]*x[i,j] for i,j in A), GRB.MINIMIZE)

  # #constraints
  con1_1 = m.addConstrs(quicksum(x[i,j] for j in V if j!=i)==1 for i in N)
  con1_2 = m.addConstrs(quicksum(x[i,j] for i in V if i!=j)==1 for j in V)
  con2_1 = m.addConstrs(quicksum(x[i,j] for j in V if j!=i)==1 for i in E)
  con2_2 = m.addConstrs(quicksum(x[i,j] for i in V if i!=j)==1 for j in E)
  con3 = m.addConstrs((x[i,j] == 1) >> (x[i,j] == 0) for i,j in A if i in E and j in E and i!=j)
  con4 = m.addConstrs((x[i,j] == 1) >> (u[i]-u[j]+(Q*x[i,j])==Q-1) for i,j in A if i not in E and j not in E and i!=j)

  def subtour(edges):
    visited = [False]*v
    cycles = []
    lengths = []
    selected = [[] for i in range(v)]
    for x,y in edges:
      selected[x].append(y)
    while True:
      current = visited.index(False)
      for i in range(v):
        if visited[i] == False:
          neighbors = [x for x in selected[i]]
          if len(neighbors) == 1:
            current = i
      thiscycle = [current]
      while True:
        visited[current] = True
        neighbors = [x for x in selected[current] if not visited[x]]
        if len(neighbors) == 0:
          break
        current = neighbors[0]
        thiscycle.append(current)
      cycles.append(thiscycle)
      lengths.append(len(thiscycle))
      if sum(lengths) == v:
        break
    return cycles

  def subtourelim(model, where):
    if where == GRB.callback.MIPSOL:
      selected = []
      # make a list of edges selected in the solution
      for i in V:
        for j in V:
          if (i != j):
            sol = model.cbGetSolution(x[i,j])
            if sol > 0.5:
              selected += [(i,j)]
      tours = subtour(selected)
      print('--------TOURS-----------')
      print(tours)
      for t in tours:
        SUnion = []
        I = []
        for node in t:
          if node in N:
            SUnion.append(node)
          else: 
            I.append(node)
        S = SUnion[1:-1]
        if len(I) == 0 and len(t)>1:
          print('no empoloyees')
          model.cbLazy(quicksum(x[i,j] for i,j in itertools.combinations(t, 2))<= len(t)-1)
        elif len(I)>=2 and len(SUnion) == 1:
          model.cbLazy(x[I[0],SUnion[0]] + quicksum(x[i,SUnion[0]] for i in E if i!=I[0])<=1)
        elif len(S)>0 and len(I)>=2:
          print('more than 1 employee, more than 2 clients')
          model.cbLazy(x[I[0],SUnion[0]] + quicksum(x[i,j] for i in E for j in SUnion if i!=I[0])<=1)
        elif len(SUnion) == 2 and len(I)>=2:
          print('only 2 clients and 2 employees')
          model.cbLazy(x[I[0],SUnion[0]] + 3*x[SUnion[0],SUnion[1]] + quicksum(x[i,SUnion[1]] for i in E if i!=I[0])<= 4)    

  # Optimize
  m._vars = m.getVars()
  m.params.LazyConstraints = 1
  # m.params.Threads = 1
  m.params.Cuts = 0
  m.optimize(subtourelim)
  status = m.status

  if status == GRB.Status.UNBOUNDED:
      print('The model cannot be solved because it is unbounded')
      exit(0)
  if status == GRB.Status.OPTIMAL:
      print('The optimal objective is %g' % m.objVal)
      sol = m.getAttr('x', x)
      selected = [i for i in sol if sol[i] > 0.5]
      finalTour = subtour(selected)
      print('---------FINAL TOUR-----------')
      print(finalTour)
      print(selected)
      for i in selected:
        plt.plot((locations[i[0]][0],locations[i[1]][0]), (locations[i[0]][1],locations[i[1]][1]), color='r')
      plt.show()
      exit(0)
  if status != GRB.Status.INF_OR_UNBD and status != GRB.Status.INFEASIBLE:
      print('Optimization was stopped with status %d' % status)
      exit(0)

  print('The model is infeasible; relaxing the constraints')
  m.feasRelaxS(0, False, False, True)
  # m.feasRelaxS(2, True, False, True)
  # m.relax()
  m.optimize(subtourelim)
  status = m.status

  if status == GRB.Status.OPTIMAL:
      print('The optimal objective is %g' % m.objVal)
      sol = m.getAttr('x', x)
      selected = [i for i in sol if sol[i] > 0.5]
      finalTour = subtour(selected)
      print('---------FINAL TOUR-----------')
      print(finalTour)
      print(selected)
      for i in selected:
        plt.plot((locations[i[0]][0],locations[i[1]][0]), (locations[i[0]][1],locations[i[1]][1]), color='r')
      plt.show()
      exit(0)

  if status in (GRB.Status.INF_OR_UNBD, GRB.Status.INFEASIBLE, GRB.Status.UNBOUNDED):
      print('The relaxed model cannot be solved \
            because it is infeasible or unbounded')
      exit(1)

  if status != GRB.Status.OPTIMAL:
      print('Optimization was stopped with status %d' % status)
      exit(1)



def makeRAssignments():
  API_key = 'AIzaSyB9sCDlGCG0hnDydbCAXAko3ogG34C4-0w'#enter Google Maps API key
  gmaps = googlemaps.Client(key=API_key)
  
  n = 10
  e = 5
  Q = n/e
  N = [i for i in range(n)]
  E = [i for i in range(n, n+e)]
  v = n+e
  V = N+E
  A = [(i,j) for i in V for j in V if i != j]
  loc_x = np.random.uniform(low=50, high=51, size=(v))
  loc_y = np.random.uniform(low=-3, high=-4, size=(v))
  locations = {}
  for i in range(v):
    locations[i] = [(loc_x[i], loc_y[i])]
  c = {(i,j): gmaps.distance_matrix(locations[i], locations[j], mode='walking')["rows"][0]["elements"][0]["distance"]["value"] for i,j in A}
  # c = {(i,j): gmaps.distance_matrix(locations[i], locations[j], mode='walking')["rows"][0]["elements"][0]["distance"]["value"] for i,j in A}
  #place the map in the middle of Cardiff
  # gmap = gmplot.GoogleMapPlotter(51.481583, -3.179090, 13)

  # print(top_attraction_lats)
  # gmap.scatter(top_attraction_lats, top_attraction_lons, '#3B0B39', size=40, marker=False)
  # lat_long = []
  # for i in V:
  #  lat_long.append(locations[i])
  # top_attraction_lats, top_attraction_lons = zip(*lat_long)
  # gmap.scatter(top_attraction_lats, top_attraction_lons, '#3B0B39', size=40, marker=True)
  # gmap.draw("my_map.html")
  for i in N:
    plt.plot(locations[i][0], locations[i][1], c='b', marker='o')
    plt.annotate('c=%d'%(i),(locations[i][0], locations[i][1]))
  for i in E:
    print(locations[i][0])
    plt.plot(locations[i][0], locations[i][1], c='r', marker='s')
    plt.annotate('e=%d'%(i),(locations[i][0], locations[i][1]))
  plt.axis('equal')
  #create model
  m = Model()

  # set variables
  x=m.addVars(A, vtype=GRB.BINARY, name='x')
  u=m.addVars(V, ub=Q, vtype=GRB.INTEGER, name='u')

  m.update()

  # #minimize problem 
  m.setObjective(quicksum(c[i,j]*x[i,j] for i,j in A), GRB.MINIMIZE)

  # #constraints
  con1_1 = m.addConstrs(quicksum(x[i,j] for j in V if j!=i)==1 for i in N)
  con1_2 = m.addConstrs(quicksum(x[i,j] for i in V if i!=j)==1 for j in V)
  con2_1 = m.addConstrs(quicksum(x[i,j] for j in V if j!=i)==1 for i in E)
  con2_2 = m.addConstrs(quicksum(x[i,j] for i in V if i!=j)==1 for j in E)
  con3 = m.addConstrs((x[i,j] == 1) >> (x[i,j] == 0) for i,j in A if i in E and j in E and i!=j)
  con4 = m.addConstrs((x[i,j] == 1) >> (u[i]-u[j]+(Q*x[i,j])==Q-1) for i,j in A if i not in E and j not in E and i!=j)

  def subtour(edges):
    visited = [False]*v
    cycles = []
    lengths = []
    selected = [[] for i in range(v)]
    for x,y in edges:
      selected[x].append(y)
    while True:
      current = visited.index(False)
      for i in range(v):
        if visited[i] == False:
          neighbors = [x for x in selected[i]]
          if len(neighbors) == 1:
            current = i
      thiscycle = [current]
      while True:
        visited[current] = True
        neighbors = [x for x in selected[current] if not visited[x]]
        if len(neighbors) == 0:
          break
        current = neighbors[0]
        thiscycle.append(current)
      cycles.append(thiscycle)
      lengths.append(len(thiscycle))
      if sum(lengths) == v:
        break
    return cycles

  def subtourelim(model, where):
    if where == GRB.callback.MIPSOL:
      selected = []
      # make a list of edges selected in the solution
      for i in V:
        for j in V:
          if (i != j):
            sol = model.cbGetSolution(x[i,j])
            if sol > 0.5:
              selected += [(i,j)]
      tours = subtour(selected)
      print('--------TOURS-----------')
      print(tours)
      for t in tours:
        SUnion = []
        I = []
        for node in t:
          if node in N:
            SUnion.append(node)
          else: 
            I.append(node)
        S = SUnion[1:-1]
        if len(I) == 0 and len(t)>1:
          print('no empoloyees')
          model.cbLazy(quicksum(x[i,j] for i,j in itertools.combinations(t, 2))<= len(t)-1)
        elif len(I)>=2 and len(SUnion) == 1:
          model.cbLazy(x[I[0],SUnion[0]] + quicksum(x[i,SUnion[0]] for i in E if i!=I[0])<=1)
        elif len(S)>0 and len(I)>=2:
          print('more than 1 employee, more than 2 clients')
          model.cbLazy(x[I[0],SUnion[0]] + quicksum(x[i,j] for i in E for j in SUnion if i!=I[0])<=1)
        elif len(SUnion) == 2 and len(I)>=2:
          print('only 2 clients and 2 employees')
          model.cbLazy(x[I[0],SUnion[0]] + 3*x[SUnion[0],SUnion[1]] + quicksum(x[i,SUnion[1]] for i in E if i!=I[0])<= 4)    

  # Optimize
  m._vars = m.getVars()
  m.params.LazyConstraints = 1
  # m.params.Threads = 1
  m.params.Cuts = 0
  m.optimize(subtourelim)
  status = m.status

  if status == GRB.Status.UNBOUNDED:
      print('The model cannot be solved because it is unbounded')
      exit(0)
  if status == GRB.Status.OPTIMAL:
      print('The optimal objective is %g' % m.objVal)
      sol = m.getAttr('x', x)
      selected = [i for i in sol if sol[i] > 0.5]
      finalTour = subtour(selected)
      print('---------FINAL TOUR-----------')
      print(finalTour)
      print(selected)
      for i in selected:
        plt.plot((locations[i[0]][0],locations[i[1]][0]), (locations[i[0]][1],locations[i[1]][1]), color='r')
      plt.show()
      exit(0)
  if status != GRB.Status.INF_OR_UNBD and status != GRB.Status.INFEASIBLE:
      print('Optimization was stopped with status %d' % status)
      exit(0)

  print('The model is infeasible; relaxing the constraints')
  m.feasRelaxS(0, False, False, True)
  # m.feasRelaxS(2, True, False, True)
  # m.relax()
  m.optimize(subtourelim)
  status = m.status

  if status == GRB.Status.OPTIMAL:
      print('The optimal objective is %g' % m.objVal)
      sol = m.getAttr('x', x)
      selected = [i for i in sol if sol[i] > 0.5]
      finalTour = subtour(selected)
      print('---------FINAL TOUR-----------')
      print(finalTour)
      print(selected)
      for i in selected:
        plt.plot((locations[i[0]][0],locations[i[1]][0]), (locations[i[0]][1],locations[i[1]][1]), color='r')
      plt.show()
      exit(0)

  if status in (GRB.Status.INF_OR_UNBD, GRB.Status.INFEASIBLE, GRB.Status.UNBOUNDED):
      print('The relaxed model cannot be solved \
            because it is infeasible or unbounded')
      exit(1)

  if status != GRB.Status.OPTIMAL:
      print('Optimization was stopped with status %d' % status)
      exit(1)
# makeRAssignments()