import simpy
import numpy
import random
import time
from matplotlib import pyplot as plt

SIM_TIME = 1*24*60*60

class Generator(object):

    def __init__(self,tGuard, uDelay, tLanding, tTakeoff, uTA, env, res, res3):
        self.tGuard = tGuard
        self.uDelay = uDelay
        self.tLanding = tLanding
        self.tTakeoff = tTakeoff
        self.uTA = uTA
        self.env = env
        self.action = self.env.process(self.run(res, res3))
        self.interArrivalTimesX = []
        self.interArrivalTimesY = []
    

    def run(self, res, res3):
        while self.env.now != SIM_TIME:
            timeCheck = self.is_time_between(0,5)

            if timeCheck:
                yield self.env.timeout(1)
                continue

            if random.random() < 0.5: #Implementerer Pdelay, må manuelt endre
                xDelay = numpy.random.gamma(3,self.uDelay/3)
            else:
                xDelay = 0

            print('Schedule plane at {} with delay: {} seconds'.format(time.strftime('%H:%M:%S', time.gmtime(self.env.now)), xDelay))
            Plane(xDelay,self.tLanding, self.tTakeoff, self.uTA, self.env, res, res3)

            t = self.ned()
            if t > self.tGuard:
                print('Wait {} seconds'.format(t))
                self.interArrivalTimesX.append(self.env.now)
                self.interArrivalTimesY.append(t)
                yield self.env.timeout(t)
            else:
                print('Wait {} seconds'.format(self.tGuard))
                self.interArrivalTimesX.append(self.env.now)
                self.interArrivalTimesY.append(self.tGuard)
                yield self.env.timeout(self.tGuard)


    def ned(self):
        beta = 0

        if self.is_time_between(5, 8):
            beta=120
        if self.is_time_between(8, 11):
            beta=30
        if self.is_time_between(11, 15):
            beta=150
        if self.is_time_between(15, 20):
            beta=30
        if self.is_time_between(20, 24):
            beta=120

        return numpy.random.exponential(beta)
    
    def is_time_between(self, beginTimeInt, endTimeInt):
        checkTime = self.env.now%86400
        beginTime = beginTimeInt*60*60
        endTime = endTimeInt*60*60

        if beginTime < endTime:
            return checkTime >= beginTime and checkTime < endTime

        else: # crosses midnight
            return checkTime >= beginTime or checkTime < endTime

    
class Plane(object):

    landingQueueTimes=[]
    takeoffQueueTimes=[]

    def __init__(self,xDelay, tLanding,tTakeoff, uTA, env, res, res3):
        self.tLanding = tLanding
        self.tTakeoff = tTakeoff
        self.uTA = uTA
        self.env = env
        self.xDelay = xDelay
        self.action = env.process(self.run(res, res3))
        
    def run(self, res, res3):
        priority = 2
        yield self.env.timeout(self.xDelay)
        reqTime = self.env.now

        with res.request(priority = priority) as req:
            print('Requesting landing-strip at {} with priority={}'.format(str(time.strftime('%H:%M:%S', time.gmtime(self.env.now))), str(priority)))
            yield req
            print('Got landing-strip at {}'.format(time.strftime('%H:%M:%S', time.gmtime(self.env.now))))
            print('Plane is landing')
            Plane.landingQueueTimes.append(self.env.now-reqTime)
            yield self.env.timeout(self.tLanding)
        
        priority=3
        print('Plane has landed and turns around')
        yield self.env.timeout(numpy.random.gamma(7,self.uTA/7))           
        
        #Kommenter ut dette for å fjerne deicing
        with res3.request() as req:
            print('Requesting deicing-truck at {}'.format(str(time.strftime('%H:%M:%S', time.gmtime(self.env.now)))))
            yield req
            print('Got deicing-truck at {}'.format(str(time.strftime('%H:%M:%S', time.gmtime(self.env.now)))))
            yield self.env.timeout(10*60)            
        
        reqTime=self.env.now
        with res.request(priority=priority) as req:
            print('Requesting landing-strip at {} with priority={}'.format(str(time.strftime('%H:%M:%S', time.gmtime(self.env.now))), str(priority)))
            yield req
            print('Got landing-strip at {}'.format(str(time.strftime('%H:%M:%S', time.gmtime(self.env.now)))))
            print('Plane is taking off')
            Plane.takeoffQueueTimes.append(self.env.now-reqTime)
            yield self.env.timeout(self.tTakeoff)


class Weather(object):
    def __init__(self, tW1, tW2, tSnow, env, res, res2, tP):
        self.tW1 = tW1
        self.tW2 = tW2
        self.tSnow = tSnow
        self.env = env
        self.tP = tP
        self.action = env.process(self.run(res, res2))


    def run(self, res, res2):
        while self.env.now!=SIM_TIME:
            timeCheck = self.is_time_between(0,5)
            if timeCheck:
                yield self.env.timeout(1)
                continue

            waitSnow=numpy.random.exponential(self.tW1)
            snowBeforeDeploy=numpy.random.exponential(self.tSnow)
            print("Snowing for {} seconds".format(waitSnow))

            if waitSnow >= snowBeforeDeploy:
                extraDelay = waitSnow-snowBeforeDeploy #Her defineres delayen før man faktisk deployer trucks
                yield self.env.timeout(snowBeforeDeploy)
                print("Too much snow, all landing-strips occupied.")

                for i in range(0,res.capacity):
                    PlowTruck(self.env, res, res2, self.tP, extraDelay)

                yield self.env.timeout(extraDelay)

            else:
                yield self.env.timeout(waitSnow)   
                
            waitSnow=numpy.random.exponential(self.tW2)
            print("Stopped snowing, will start in {} seconds".format(waitSnow))
            yield self.env.timeout(waitSnow)


    def is_time_between(self, beginTimeInt, endTimeInt):
        checkTime = self.env.now%86400
        beginTime=beginTimeInt*60*60
        endTime=endTimeInt*60*60

        if beginTime < endTime:
            return checkTime >= beginTime and checkTime < endTime
        else: # crosses midnight
            return checkTime >= beginTime or checkTime < endTime


class PlowTruck(object):
    def __init__(self, env, res1, res2, tP, extraDelay):
        self.env=env
        self.tP=tP
        self.extraDelay=extraDelay
        self.priority=1
        self.action = env.process(self.run(res1, res2))
     
        
    def run(self, res1, res2):
        request=res1.request(priority=self.priority)
        print('Requesting landing-strip at {} with priority={}'.format(str(time.strftime('%H:%M:%S', time.gmtime(self.env.now))), str(self.priority)))
        yield request
        print('Snow got landing-strip at {}'.format(str(time.strftime('%H:%M:%S', time.gmtime(self.env.now)))))
        yield self.env.timeout(self.extraDelay)
        request2=res2.request()
        print('Requesting plow-truck at {}'.format(str(time.strftime('%H:%M:%S', time.gmtime(self.env.now)))))
        yield request2
        print('Got plow-truck at {}'.format(str(time.strftime('%H:%M:%S', time.gmtime(self.env.now)))))
        yield self.env.timeout(self.tP)
        print("Plowing-truck finished plowing")
        res2.release(request2)
        res1.release(request)


#Program for å teste interarrival-times påvirkning av delays
for i in range(0,480,+60):
    env = simpy.Environment()
    res = simpy.PriorityResource(env, capacity=2)
    res3 = simpy.Resource(env, capacity=1)
    gen = Generator(60,i,60,60,60*45,env, res, res3)
    env.run(until=SIM_TIME)
    plt.figure(i)
    plt.scatter(gen.interArrivalTimesX, gen.interArrivalTimesY)
    plt.show()
"""

#Program for å teste delays virkning på tiden et fly venter fra den requester til den får landing-strip
#for fly som skal lande og ta av
avgQueueTimesL=[]
avgQueueTimesT=[]
delays=[]
for i in range(0,480,20):
    Plane.landingQueueTimes=[]
    Plane.takeoffQueueTimes=[]
    delays.append(i)
    env = simpy.Environment()
    res = simpy.PriorityResource(env, capacity=2)
    res3=simpy.Resource(env, capacity=1)
    gen = Generator(60,i,60,60,60*45,env, res, res3)
    env.run(until=SIM_TIME)
    avgQueueTime=numpy.mean(Plane.landingQueueTimes)
    avgQueueTimesL.append(avgQueueTime)
    avgQueueTime=numpy.mean(Plane.takeoffQueueTimes)
    avgQueueTimesT.append(avgQueueTime)
plt.figure(9)    
plt.plot(delays,avgQueueTimesL)
plt.figure(10)  
plt.plot(delays,avgQueueTimesT)
"""
"""
#Bad weather
avgQueueTimesL=[]
avgQueueTimesT=[]
delays=[]
for i in range(0,480,20):
    Plane.landingQueueTimes=[]
    Plane.takeoffQueueTimes=[]
    delays.append(i)
    env = simpy.Environment()
    res = simpy.PriorityResource(env, capacity=2)
    res2=simpy.Resource(env, capacity=1)
    res3=simpy.Resource(env, capacity=1)
    gen = Generator(60,i,60,60,60*45,env, res, res3)
    Weather(60*60, 120*60, 45*60, env, res, res2, 10*60)
    env.run(until=SIM_TIME)
    avgQueueTime=numpy.mean(Plane.landingQueueTimes)
    avgQueueTimesL.append(avgQueueTime)
    avgQueueTime=numpy.mean(Plane.takeoffQueueTimes)
    avgQueueTimesT.append(avgQueueTime)
plt.figure(11)
plt.plot(delays,avgQueueTimesL)
plt.figure(12)
plt.plot(delays,avgQueueTimesT)
"""
        
