from os import O_CREAT, access
from turtle import forward
import networkx as nx
import argparse
import os
import torch
import torch.optim as optim
import torch.nn as nn
import torch.nn.functional as F
import matplotlib.pyplot as plt
import random
#used as a lookup table for one hot encoding of allocation types
options = {
        "STACK":0,
        "STACK_FRAME":1,
        "STACK_ARGS":2,
        "STACK_PAGE":3,
        "GEN_HEAP":4,
        "UFO_HEAP":5,
        "GLOBAL":6,
        "KMALLOC":7,
        "KMALLOC_ND":8,
        "KMEM_CACHE":9,
        "KMEM_CACHE_ND":10,
        "ALLOC_PAGES":11,
        "VMALLOC":12,
        "INDUCED_ALLOC":13,
        "BOOTMEM":14,
        "MEMBLOCK":15,
        "UFO_MEMBLOCK":16,
        "MEMORIZER":17,
        "USER":18,
        "BUG":19,
        "UFO_GLOBAL":20,
        "UFO_NONE":21,
        "NONE":22,
        "ALLOC TYPE NOT FOUND":23
    }

def oneHotAlloc(allocType):
    oneHot = [0 for i in range(24)]
    global options
    oneHot[options[allocType]] = 1.0
    return tuple(oneHot)

#oh I'm sure this is an awful implementation but we'll see what happens
#node = (pid,process)
#line = [alloc_ip,alloc_pid,va,size,alloc_time,free_time,alloc_type,process,slab_type]
def addNewNode(G,node,line):
    oneHot = oneHotAlloc(line[7])
    #dict = {"size":line[3],"alloc_time":line[4],"free_time":line[5],"alloc_type":oneHot}
    G.add_node(node,size=line[3],alloc_time=line[4],free_time=line[5],alloc_type=oneHot)
    return G

#attributes = [instr_ip,writes,reads]
#pointA - source
#pointB - target
def addNewEdge(G,pointA,pointB,attributes):
    if not G.has_edge(pointA,pointB) and len(attributes) == 4:
        G.add_edge(pointA,pointB,writes=float(attributes[2]),reads=float(attributes[3]))
    elif not G.has_edge(pointA,pointB) and len(attributes) == 3:
        G.add_edge(pointA,pointB,writes=float(attributes[1]),reads=float(attributes[2]))
    #update edges
    elif len(attributes) == 4:
        G[pointA][pointB]["writes"] += float(attributes[2])
        G[pointA][pointB]["reads"] += float(attributes[3])
    else: 
        G[pointA][pointB]["writes"] += float(attributes[1])
        G[pointA][pointB]["reads"] += float(attributes[2])
    return G

#kmap - file path to the kmap that we want to analyze
def createGraph(kmap):
    G = nx.Graph()
    #first gather all nodes
    node_colors = []
    with open(kmap,'r') as f:
        for line in f:
            currLine = line.strip().split(',')
            #10 things means that we have found an object and if it doesn't exist already we add it
            if len(currLine) == 10:
                node = (currLine[0])
                oneHot = oneHotAlloc(currLine[7])
                if not G.has_node(node):
                    G.add_node(node,size=float(currLine[3]),alloc_time=float(currLine[4]),free_time=float(currLine[5]),alloc_type=oneHot,name=currLine[8])
                    if "exploit" in line:
                        node_colors.append("tab:green")
                    else:
                        node_colors.append("tab:red")
                #if the node already exists then update some of its attributes
                else:
                    G.nodes[node]["size"] += float(currLine[3])
                    G.nodes[node]["alloc_time"] = float(min(G.nodes[node]["alloc_time"],float(currLine[4])))
                    G.nodes[node]["free_time"] = float(max(G.nodes[node]["free_time"],float(currLine[5])))
            #if the length is 4 then we have a source node
            if len(currLine) == 4 or len(currLine) == 3:
                #print("yeetdab")
                if not G.has_node(currLine[0]):
                    G.add_node(currLine[0],size=0,alloc_time=1,free_time=1,alloc_type=oneHotAlloc("BUG"),name="read/write")
                    node_colors.append("tab:blue")
                if not G.has_edge(node,currLine[0]) and len(currLine) == 4:
                    G.add_edge(node,currLine[0],writes=float(currLine[2]),reads=float(currLine[3]))
                elif not G.has_edge(node,currLine[0]) and len(currLine) == 3:
                    G.add_edge(node,currLine[0],writes=float(currLine[1]),reads=float(currLine[2]))
    #update edges
                elif len(currLine) == 4:
                    G[node][currLine[0]]["writes"] += float(currLine[2])
                    G[node][currLine[0]]["reads"] += float(currLine[3])
                else: 
                    G[node][currLine[0]]["writes"] += float(currLine[1])
                    G[node][currLine[0]]["reads"] += float(currLine[2])
        f.close()
    return G,node_colors
#really simple GNN layer, guess I can tune it as things go
#currently following the Stanford suggested architecture of:
#linear -> batchnorm -> dropout -> activation(ReLU in this case) -> attention
class GraphLayer(nn.Module):
    #graph layer that we'll use for each one duh
    def __init__(self,size_in,size_out,heads):
        super(GraphLayer,self).__init__()
        self.size_in,self.size_out = size_in,size_out
        self.size_out = size_out
        self.heads = heads
        self.network = nn.Sequential(
            nn.Linear(size_in,size_out*heads,bias=True),
            #nn.BatchNorm1d(size_out*heads),
            nn.Dropout(0.2),
            nn.LeakyReLU(0.02)).to('cuda')
        self.head = nn.MultiheadAttention(size_out*heads,heads).to('cuda')
    def forward(self,node_features):
        #print(node_features.shape,type(node_features))
        outcome = self.network(node_features)
        outcome, _ = self.head(outcome,outcome,outcome)
        outcome = outcome.view(outcome.shape[0],self.size_out*self.heads).mean(dim=0)
        return outcome
    
class kmapGNN(nn.Module):
    def __init__(self,size_in,size_hidden,size_out,heads,linear_hidden,kmapFile,lr):
        super(kmapGNN,self).__init__()
        self._dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.size_in,self.size_hidden,self.size_out,self.heads = size_in,size_hidden,size_out,heads
        self.secondNeighbors = GraphLayer(size_in,size_hidden,heads).to('cuda')
        self.firstNeighbors = GraphLayer(size_hidden*heads,int(size_out/heads),heads).to('cuda')
        #takes in embedded node information and does something with it
        self.classification = nn.Sequential(
            nn.Linear(size_out,linear_hidden,bias=True),
            #nn.BatchNorm1d(linear_hidden),
            nn.LeakyReLU(0.02),
            nn.Linear(linear_hidden,linear_hidden,bias=True),
            #nn.BatchNorm1d(linear_hidden),
            nn.LeakyReLU(0.02),
            nn.Linear(linear_hidden,2,bias=True),
            nn.Softmax()
        ).to('cuda')
        self.secondOptim = optim.SGD(self.secondNeighbors.parameters(),lr=lr)
        self.firstOptim = optim.SGD(self.firstNeighbors.parameters(),lr=lr)
        self.classOptim = optim.SGD(self.classification.parameters(),lr=lr)
        self.lossFn = nn.CrossEntropyLoss()
        self.kmapFile = kmapFile
        self.G = nx.Graph()
        self.order = []
        self.numEpochs = 0
    #initialize a graph from a given kmap (TODO: allow for new kmaps to be given)
    def initGraph(self):
        self.G,self.colors= createGraph(self.kmapFile)

    #randomize order in which nodes are "classified"
    def getNewOrder(self):
        print("reshuffuling")
        self.order = [key for key in self.G.nodes.keys()]

        random.shuffle(self.order)
        return
    def reformatNodeInfo(self,nodeData):
        reformatted = []
        vals = list(nodeData.values())
        for data in range(0,len(vals)-2):
            reformatted.append(float(vals[data]))
        reformatted = reformatted + list(nodeData["alloc_type"])
        return torch.as_tensor(reformatted,dtype=torch.float32).to('cuda')

    def convertToNodeFormat(self,nodeData):
        converted = {}
        oneHotish = []
        converted["size"] = nodeData[0]
        converted["alloc_time"] = nodeData[1]
        converted["free_time"] = nodeData[2]
        for data in nodeData[3:]:
            oneHotish.append(data)
        converted["alloc_type"] = oneHotish
        return converted
    
    def do(self,batchSize=5):

        #if all nodes have been traversed
        if len(self.order)== 0:
            self.getNewOrder()
            self.numEpochs += 1
            print("EPOCH: ",self.numEpochs)
        self.firstOptim.zero_grad()
        self.secondOptim.zero_grad()
        self.classOptim.zero_grad()
        loss = 0
        #pop next node off queue
        for nodeNum in range(batchSize):
            currNode = self.order.pop(0)
            #accumulate neighbors
            neighbors = self.G.neighbors(currNode)
            tempNodeChange = []
            
            
            for neighbor in neighbors:
                neighborsSquared = self.G.neighbors(neighbor)
                #skip neighborless nodes
                neighborsSquared = list(neighborsSquared)
                if len(neighborsSquared) == 0:
                    continue
                together = self.reformatNodeInfo(self.G.nodes[neighborsSquared[0]]).to('cuda')
                together = together.view((1,27))
                for neighborTwo in neighborsSquared:
                    if neighborTwo == neighborsSquared[0]:
                        continue
                    else:
                        together = torch.cat((together,self.reformatNodeInfo(self.G.nodes[neighborTwo]).view(1,27)),dim=0).to('cuda')

                if len(tempNodeChange) == 0:
                    tempNodeChange = self.secondNeighbors(together.to('cuda')).view(1,300)
                else:
                    tempNodeChange = torch.cat((tempNodeChange,self.secondNeighbors(together.to('cuda')).view(1,300)),dim=0).to('cuda')
            if len(tempNodeChange) != 0:
                embedding = self.firstNeighbors(torch.as_tensor(tempNodeChange).to('cuda'))

                #update node
                updated = self.convertToNodeFormat(embedding)
                for key in updated.keys():
                    if key != "name":
                        self.G.nodes(data=True)[currNode][key] = updated[key]
                guess = self.classification(embedding.float()).view((1,2))
                truth = torch.zeros((1,2)).to('cuda')
                if "exploit" in self.G.nodes(data=True)[currNode]["name"] :
                    print("found exploit")
                    truth[0][0] = 1
                else:
                    truth[0][1] = 1
                loss += self.lossFn(guess,truth)
        print("batch loss: ",loss)
        loss.backward()
        self.firstOptim.step()
        self.secondOptim.step()
        self.classOptim.step()
            
        return
    def train(self,num_iter=1000000):
        for iter in range(num_iter):
            self.do()
        return
def main():
    model = kmapGNN(27,100,27,3,100,"exploit_08_03_2022.kmap",0.005)
    model.initGraph()
    model.train()
    G,node_colors = createGraph("exploit_08_03_2022.kmap")
    plt.figure(figsize=(200,200))
    nx.draw_spring(G,node_size=30,with_labels=False,node_color=node_colors)
    plt.savefig("exploit.png")
    return 0
main()