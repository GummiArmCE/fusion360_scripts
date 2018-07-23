#Author-frederico
#Description-

import adsk.core, adsk.fusion, traceback
import os #, sys
import re
import xml.etree.cElementTree as etree 
import xml.dom.minidom # for prettying it....

def save_to_stl(rootComp):
    global envvars
    didifail = 0
    try:
        # create a single exportManager instance
        exportMgr = envvars.design.exportManager
        
        #stlname = rootComp.name.translate(None, ':!@#$')  
        #line = re.sub('[!@#$]', '', line)
        stlname = clearupst(rootComp.name)        
        
        # export the root component to printer utility
        stlRootOptions = exportMgr.createSTLExportOptions(rootComp,  envvars.meshes_directory+'/' + stlname)
    
        # get all available print utilities
        #printUtils = stlRootOptions.availablePrintUtilities
        
        # export the root component to the print utility, instead of a specified file            
        #for printUtil in printUtils:
        #    stlRootOptions.sendToPrintUtility = True
        #   stlRootOptions.printUtility = printUtil
        stlRootOptions.sendToPrintUtility = False
        
        #exportMgr.execute(stlRootOptions)
    except:
        print('could not save stl. {}'.format(traceback.format_exc()))
        didifail = 1
    return didifail

class Link:
    def __init__(self,occ,level):
        self.name = ''
        self.inertial = Inertial()
        self.visual = Visual()
        self.collision = Collision();
        self.level = level
        self.name = clearupst(occ.name);
        superprint(self.level, 'Link: my name is:' + self.name)
        self.visual.geometryfilename = "package://somepackage/meshes/" + self.name +".stl"
        self.collision.geometryfilename = self.visual.geometryfilename # the legend has it that this file should be a slimmer version of the visuals, so that collisions can be calculated more easily.... 
        
    def makelinkxml(self, urdfroot):
    
        link = etree.SubElement(urdfroot, "link", name= self.name)

        inertial = etree.SubElement(link, "inertial")
        etree.SubElement(inertial, "origin", xyz = self.inertial.origin.xyz, rpy = self.inertial.origin.rpy  )
        etree.SubElement(inertial, "mass", value = self.inertial.mass)      
        etree.SubElement(inertial, "inertia", ixx= self.inertial.inertia.ixx, ixy= self.inertial.inertia.ixy, ixz= self.inertial.inertia.ixz, iyy= self.inertial.inertia.iyy, iyz= self.inertial.inertia.iyz, izz= self.inertial.inertia.izz )
        
        visual = etree.SubElement(link, "visual")        
        etree.SubElement(visual, "origin", xyz = self.visual.origin.xyz, rpy = self.visual.origin.rpy  )  
        geometry = etree.SubElement(visual, "geometry")
        etree.SubElement(geometry, "mesh", filename = self.visual.geometryfilename)
        material = etree.SubElement(visual, "material", name = self.visual.materialname)
        etree.SubElement(material, "color", rgba = self.visual.color)
        
        collision = etree.SubElement(link, "collision")        
        etree.SubElement(collision, "origin", xyz = self.collision.origin.xyz, rpy = self.collision.origin.rpy  )  
        geometry = etree.SubElement(collision, "geometry")
        etree.SubElement(geometry, "mesh", filename = self.visual.geometryfilename)
        #origin = etree.SubElement(inertial, "origin")
        #etree.SubElement(origin, "xyz").text = self.inertial.origin.xyz
        #etree.SubElement(origin, "rpy").text = self.inertial.origin.rpy
        
        return urdfroot
    def removestl(self, urdfroot):
        ##does nothing for the time being
        print('warning!!!! not implemented')

class Inertial:
    def __init__(self):
        self.origin = OrVec()
        self.mass = '0'
        self.inertia = Inertia()
        
class Inertia:
    def __init__(self):
        self.ixx = '0'
        self.ixy = '0'
        self.ixz = '0'
        self.iyy = '0'
        self.iyz = '0'
        self.izz = '0'
        
class OrVec:
    def __init__(self):
        self.xyz = '0 0 0'
        self.rpy = '0 0 0'
   
class Visual:
    def __init__(self):
        self.origin = OrVec()
        self.geometryfilename = ""
        self.materialname = ""
        self.color = '0 0 0 1'
        
class Collision:
    def __init__(self):
        self.origin = OrVec()
        self.geometryfilename = ""
        
class Joint:
    def __init__(self,joint,level):
        self.origin = OrVec()       
        self.parentlink = ''
        self.childlink = ''
        self.axis = '0 0 0'
        self.limit = Limit()
        self.level = level
        self.name = clearupst(joint.name)
        superprint(self.level, 'joint: my name is:' + self.name)
        #python doesnt have a switch statement, i repeat python does not have a switch statement...
        #from the docs, we should implement this:
        #Name 	Value 	Description
        #BallJointType 	6 	Specifies a ball type of joint.
        #CylindricalJointType 	3 	Specifies a cylindrical type of joint.
        #PinSlotJointType 	4 	Specifies a pin-slot type of joint.
        #PlanarJointType 	5 	Specifies a planar type of joint.
        #RevoluteJointType 	1 	Specifies a revolute type of joint.
        #RigidJointType 	0 	Specifies a rigid type of joint.
        #SliderJointType 	2 	Specifies a slider type of joint.
        if joint.jointMotion.jointType is 1:
            self.type = "revolute"
            self.axis = str(joint.jointMotion.rotationAxisVector.x)+ ' ' + str(joint.jointMotion.rotationAxisVector.y)+ ' ' + str(joint.jointMotion.rotationAxisVector.z)
        if joint.jointMotion.jointType is 0:
            self.type = "fixed"
        
        if 'rotationLimits' in dir(joint.jointMotion):
            if joint.jointMotion.rotationLimits.isMinimumValueEnabled:
                self.limit.lower = joint.jointMotion.rotationLimits.minimumValue
            if joint.jointMotion.rotationLimits.isMaximumValueEnabled:
                self.limit.upper = joint.jointMotion.rotationLimits.maximumValue
        
        
    
    def makejointxml(self, urdfroot):
    
        joint = etree.SubElement(urdfroot, "joint", name= self.name, type = self.type)
        etree.SubElement(joint, "origin", xyz = self.origin.xyz, rpy = self.origin.rpy)
        etree.SubElement(joint, "parent", link = self.parentlink)        
        etree.SubElement(joint, "child", link = self.childlink)        
        etree.SubElement(joint, "axis", xyz = self.axis)
        etree.SubElement(joint, "limit", lower = self.limit.lower, upper = self.limit.upper, effort=self.limit.effort, velocity = self.limit.velocity)
        #origin = etree.SubElement(inertial, "origin")
        #etree.SubElement(origin, "xyz").text = self.inertial.origin.xyz
        #etree.SubElement(origin, "rpy").text = self.inertial.origin.rpy
        
        return urdfroot
        
class Limit:
    def __init__(self):
        self.lower = '-1'
        self.upper = '1'
        self.effort = '0'
        self.velocity = '0'

class RigidGroupList: #list of dictionaries
    def __init__(self):
        self.rigidgroups = [];
    def size(self):
        return len(self.rigidgroups) 
    def addpart(self, linklist, level, father): ### have info, not going to do anything with it. 
        for j in range(0,len(linklist)):
            foundmygroup = False
            for i in self.rigidgroups:
                if linklist[j] in i.memberlist:
                    link2 = linklist
                    link2.pop(j)
                    i.addpart(link2,level,father)
                    foundmygroup = True
                    return
                
            ## went through all the rigidgroups and didn't find the any of the links, then i need to create a new rigidgroup
        if not foundmygroup:
            newgroup = RigidGroup()
            #newgroup.memberlist.update({link1:level, link2:level})
            newgroup.addpart(linklist,level, father)
            self.rigidgroups.append(newgroup)
#        def addpart(self, link1, link2, level):
#        foundmygroup = False
#        for i in self.rigidgroups:
#            if link1 in i.memberlist and link2 not in i.memberlist:
#                i.addpart(link2,level)
#                foundmygroup = True
#            if link2 in i.memberlist and link1 not in i.memberlist:
#                i.addpart(link1,level)
#                foundmygroup = True
#        ## went through all the rigidgroups and didn't find the any of the links, then i need to create a new rigidgroup
#        if not foundmygroup:
#            newgroup = RigidGroup()
#            newgroup.memberlist.update({link1:level, link2:level})
#            self.rigidgroups.append(newgroup)
    def condensegroups(self):
        ## might take a while. condenses groups so that links are sane
        print('condensing groups might take a while')
        finished = False
        while not finished:
             finished = self.checkcondensedgroupsfun2() ##slightly faster
        while not finished:
             finished = self.checkcondensedgroupsfun()

    def checkcondensedgroupsfun(self):
        ###internal function to do my elaborate break...
        nomerge = True
        for i in range(0, len(self.rigidgroups)):
            for j in range(i+1, len(self.rigidgroups)):
                for k in self.rigidgroups[i].memberlist:
                    if k in self.rigidgroups[j].memberlist:
                        ## then i and j should be merged!
                        self.rigidgroups[i].memberlist.update(self.rigidgroups[j].memberlist)
                        self.rigidgroups.pop(j)                        
                        nomerge = False
                        return nomerge
        return nomerge
                        
    def checkcondensedgroupsfun2(self):
        ###internal function to do my elaborate break...
        nomerge = True
        for i in range(0, len(self.rigidgroups)):
            toocc = self.rigidgroups[i].topocc()
            for j in range(i+1, len(self.rigidgroups)):
                if toocc[0] in self.rigidgroups[j].memberlist:
                    ## then i and j should be merged!
                    self.rigidgroups[i].memberlist.update(self.rigidgroups[j].memberlist)
                    self.rigidgroups.pop(j)                        
                    nomerge = False
                    return nomerge
        return nomerge
    
    def gettopocc(self,link):
        topcomps = []
        for i in self.rigidgroups:
            if link in i.memberlist: ###found my group
                topcomps.append( i.topocc())
        return topcomps
        print('error in gettopcc in RigidGroupList')
        
    def updatenames(self, jointlist, linklist):
        print('ERROR: NOT IMPLEMENTED')
        
class RigidGroup:
    def __init__(self):
        self.memberlist = {}
    def addpart(self,linklist,level,parent): ###i have this info but I am not going to do anything with it for now.
        for link in linklist:
            self.memberlist.update({link:level})
    def topocc(self):
        topcomps = []
        levels = self.memberlist.values()
        topocclevel = min(levels)
        for occ in self.memberlist:
            if self.memberlist[occ] is topocclevel:
                topcomps.append( occ)
        return topcomps
        print('error in topcc in RigidGroup')
        
# Performs a recursive traversal of an entire assembly structure.
def traverseAssembly(occurrences, currentLevel, father):
    global urdfroot
    global envvars
    jointsonthislevel = 0   
    for i in range(0, occurrences.count):
        listownjoints = []
        numjoints = 0
        ## adding name of top level occurances before in the list.        
        if 'name' not in dir(occurrences.item(i)):
            superprint(currentLevel,'Part: ERROOOOOOORRRRR:: i dont have a name')
            print(dir(occurrences.item(i)))
            occname = father + '!noname'
        else:
            #occname = father + '!'+ clearupst(occurrences.item(i).name)
            occname = clearupst(occurrences.item(i).name)
        ### updating list
        if occname not in envvars.occurrencedict:
            envvars.occurrencedict.update( {occname : currentLevel})        
        
        if occurrences.item(i).childOccurrences and envvars.recursionlimit>currentLevel:
            internaljoints = traverseAssembly(occurrences.item(i).childOccurrences, currentLevel + 1, occname)
        else:
            internaljoints = 0
            

                        
        #occ = Part(occurrences.item(i),currentLevel,envvars.recursionlimit)  
		
        ########### JOINTS REGION ###############         
        ## going through joints by occurance
        alljoints = []
        alljoints.extend(occurrences.item(i).component.asBuiltJoints)
        alljoints.extend(occurrences.item(i).component.joints)  
        alljoints.extend(occurrences.item(i).asBuiltJoints)    
        alljoints.extend(occurrences.item(i).joints)  
        for j in alljoints:    
            try: 
                if 1:
                    ##this also didn't work. 
#                # Get health state of a joint                                
#                health = j.healthState
#                if health == adsk.fusion.FeatureHealthStates.ErrorFeatureHealthState or health == adsk.fusion.FeatureHealthStates.WarningFeatureHealthState:
#                    #message = j.errorOrWarningMessage
#                    print('this joint is not healthy.')
                #else:#j.isValid: ##maybe this will remove some of the errors?
                    if j.jointMotion.jointType is not 0:
                        numjoints = numjoints + 1
                        listownjoints.append(j.name) 
                        setjoint(j,currentLevel)
                    else:
                        ### rigid joint! need to add it to rigidgrouplist
                        setrigid(j,currentLevel,father)
            except:#else:
                print('ERROR:')
                #print(dir(j) )
                superprint(currentLevel, 'error traversing joints:\n{}'.format(traceback.format_exc()))   
                
        ######### RIGIDGROUPS REGION ###########
                
                #print(dir(occurrences.item(i).rigidGroups))
        try:
            setrigidgroups(occurrences.item(i).rigidGroups,currentLevel,father)
        except:#else:
            print('ERROR:')
            #print(dir(j) )
            superprint(currentLevel, 'error traversing rigidgroups:\n{}'.format(traceback.format_exc()))   
            
        ######### LINKS REGION #################        

        if internaljoints==0:
            if numjoints>0:
                linkdefs = Link(occurrences.item(i), currentLevel) ## this has to point to the rigidgroup!
                print('decided to add a link for: ' + linkdefs.name + ' because i have ' + str(numjoints)+ ' joints')
                print(listownjoints)
                
                ##urdfroot = linkdefs.makelinkxml(urdfroot)                  
                ## not yet. will probably need to change the name of the links later because of rigidgroups. will add it to preLINKsslist
                envvars.prelinkslist.append(linkdefs)
                # I am assuming you can only have a joint between 2 objects. also reinventing the wheel here, joint might have a property telling who it links to...    
                stlnotsaved = save_to_stl(occurrences.item(i)) ## probably need to check rigidgroups?
                if stlnotsaved:
                    linkdefs.removestl(urdfroot)
            else:
            #elif not occurrences.item(i).rigidGroups: #no joints no internaljoints, no rigidgroups. sad, lets link it to its father with a rigid component
                #print('warning floating component. will add a rigid link to its father to make sure it is rendered.')
                if envvars.rigidlinkfloatingchildren:
                    envvars.rigidgrouplist.addpart([occname, father], currentLevel,father)
                

            


        ## try to clear the joint queue
        copyjointqueue = []
        for j in range(0, len(envvars.jointqueue)):
            if envvars.jointqueue[j].parentlink in envvars.occurrencedict and envvars.jointqueue[j].childlink in envvars.occurrencedict :
                copyjointqueue.append(j)                
                ##urdfroot = envvars.jointqueue[j].makejointxml(urdfroot)
                ## not yet. will probably need to change the name of the links later because of rigidgroups. will add it to prejointslist
                envvars.prejointslist.append(envvars.jointqueue[j])
        for j in reversed(range(0,len(copyjointqueue))): ##i remove it in reverse so that i don't change the indexes of the list when poping items
            envvars.jointqueue.pop(copyjointqueue[j])
            
            
            
        jointsonthislevel = jointsonthislevel + numjoints + internaljoints
    #alljointsinleaf = numjoints + internaljoints                
    return jointsonthislevel

def setjoint(actualjoint, currentLevel):
    print('I am not a rigid joint. i am a joint type' + str(actualjoint.jointMotion.jointType) )
    #global urdfroot
    global envvars
    jointdefs = Joint(actualjoint, currentLevel);
    if jointdefs.name not in envvars.jointlist:
        if actualjoint.occurrenceOne is None:
            p1 = 'base'
        else:
            p1 = clearupst(actualjoint.occurrenceOne.name)
        if actualjoint.occurrenceTwo is None:
            p2 = 'base'
        else:
            p2 = clearupst(actualjoint.occurrenceTwo.name)
        if actualjoint.occurrenceOne is None and actualjoint.occurrenceTwo is None:
            print('cannot connect base with base. error. ')
            return False
        if p1 in envvars.occurrencedict and p2 in envvars.occurrencedict :
            if envvars.occurrencedict[p1]>envvars.occurrencedict[p2]:
                jointdefs.parentlink = p2
                jointdefs.childlink = p1
            else:
                jointdefs.parentlink = p1
                jointdefs.childlink = p2
                ##urdfroot = jointdefs.makejointxml(urdfroot)
                ## not yet. will probably need to change the name of the links later because of rigidgroups. will add it to prejointslist
                envvars.prejointslist.append(jointdefs)
        else: 
            jointdefs.parentlink = p1 ### they might be flipped if i add them from the jointqueue. needs fixing!
            jointdefs.childlink = p2
            #print("joint cant be added right now. sent to queue")
            envvars.jointqueue.append(jointdefs)
        envvars.jointlist.append(jointdefs.name)
    #print(envvars.jointlist)
        
def setrigid(actualjoint, currentLevel,parent):
    ###actually this is incorrect. every rigid group should have been defined as such and rigid joints should be real rigid joints and set with the setjoint function...
    #print('I am a rigid joint. i am going to be a part of a rigid group' + str(actualjoint.jointMotion.jointType) )
    #global urdfroot
    global envvars
    #jointdefs = Joint(actualjoint, currentLevel);

    if actualjoint.occurrenceOne is None:
        p1 = 'base'
    else:
        p1 = clearupst(actualjoint.occurrenceOne.name)
    if actualjoint.occurrenceTwo is None:
        p2 = 'base'
    else:
        p2 = clearupst(actualjoint.occurrenceTwo.name)
    if actualjoint.occurrenceOne is None and actualjoint.occurrenceTwo is None:
        print('cannot connect base with base. error. ')
        return False
    envvars.rigidgrouplist.addpart([p1,p2],currentLevel, parent)
    #envvars.rigidgrouplist.condensegroups() 					

def setrigidgroups(rigidgrouplistobj,level,parent):
    for rigidgroupobj in rigidgrouplistobj:
        alloc = rigidgroupobj.occurrences
        if len(alloc) is 1:
            print('funny, a group with one member')            
            envvars.rigidgrouplist.addpart([clearupst(alloc.name)],level,parent)
        else:
            allocnlist= [];
            for occ in alloc:
                allocnlist.append(occ.name)
            envvars.rigidgrouplist.addpart(allocnlist,level,parent)


def superprint(level,stringo):
    print(spaces(level*5)+stringo)


        
def clearupst(stringo):
    strstr = re.sub('[:!@#$]', '',stringo)
    strstr = re.sub(' ', '_',strstr)
    return strstr

# Returns a string containing the especified number of spaces.
def spaces(spaceCount):
    result = ''
    for i in range(0, spaceCount):
        result += ' '

    return result

class Envvars:
    def __init__(self):
        self.recursionlimit = 20
        self.meshes_directory = ''
        self.occurrencedict = {'base': 0}
        self.jointqueue = []
        self.jointlist = [] # to make sure i will only place joints once.
        self.mobilelist = []
        self.rigidlist = []
        self.design = ''
        self.rigidgrouplist = RigidGroupList()
        self.prejointslist = []
        self.prelinkslist = []
        self.rigidlinkfloatingchildren = True ### set if you want to create a rigid link with children that do not have any joint or rigid link
        self.rigidlinkfloatinggroups = False
        
def run(context):
    global urdfroot
    global envvars
    ui = None
    #print('heloo!')
    try:
        envvars = Envvars();
        base_directory = "c:/test_gummi_urdf"
        if not os.path.exists(base_directory):
            os.makedirs(base_directory)
        envvars.meshes_directory = "c:/test_gummi_urdf/meshes"
        if not os.path.exists(envvars.meshes_directory):
            os.makedirs(envvars.meshes_directory)           
                    
            
        app = adsk.core.Application.get()
        ui  = app.userInterface
        
        product = app.activeProduct
        envvars.design = adsk.fusion.Design.cast(product)
        if not envvars.design:
            ui.messageBox('No active Fusion design', 'No Design')
            return

        # Get the root component of the active design.
        rootComp = envvars.design.rootComponent
        
        # Create the title for the output.
        print( 'Assembly structure of ' + envvars.design.parentDocument.name + '\n')
        
        urdfroot = etree.Element("robot", name = "gummi")        
     
                
        # Call the recursive function to traverse the assembly and build the output string.
        traverseAssembly(rootComp.occurrences.asList, 1, clearupst(rootComp.name))

        if len(envvars.jointqueue)>0:
            print('there is a couple of stuff i didnt put in the urdf...')        
            print(envvars.jointqueue)
        
        #print(envvars.occurrencedict)
        print(envvars.jointlist)

        ##this will take a while
        envvars.rigidgrouplist.condensegroups()
        ##also need to update joint and link names
        envvars.rigidgrouplist.updatenames(envvars.prejointslist, envvars.prelinkslist)
        if envvars.rigidlinkfloatinggroups:
            print('ERROR: NOT IMPLEMENTED')
        print('found ' + str(envvars.rigidgrouplist.size()) + ' rigidgroups')
        print('__________________________')
        print('__________________________')
        for i in range(0,envvars.rigidgrouplist.size()):
            print('__________________________')
            print(envvars.rigidgrouplist.rigidgroups[i].topocc())
            print('__________________________')
            print(envvars.rigidgrouplist.rigidgroups[i].memberlist)
            print('__________________________')
        #only after condensing groups I can generate the links and the joints. 
        for jointdefs in envvars.prejointslist:
            urdfroot = jointdefs.makejointxml(urdfroot)
        for linkdefs in envvars.prelinkslist:
            urdfroot = linkdefs.makelinkxml(urdfroot)
        
        tree = etree.ElementTree(urdfroot)     
        root = tree.getroot()
        treestring = etree.tostring(root)
        #treestring = str(root)
        
        #ui.messageBox(treestring)
        xmldomtype = xml.dom.minidom.parseString(treestring)
        pretty_xml_as_string = xmldomtype.toprettyxml()
        #prettytree = etree();
        #prettytree = etree.fromstring(pretty_xml_as_string)
        #prettytree.write("c:/test/robot.urdf")
        
        with open(base_directory +"/robot.urdf", "w") as text_file:
            print(pretty_xml_as_string, file=text_file)        
        
        
        #ui.messageBox(resultString)
       
    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))