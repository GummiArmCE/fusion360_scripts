#Author- Frederico B. Klein
#Description- URDFGEN command - somewhat functional.
import adsk.core, adsk.fusion, traceback
import xml.etree.cElementTree as etree
import xml.dom.minidom # for prettying it....
import inspect
import logging
import re
import os , sys
#from copy import deepcopy ### pickle cant copy any swig object...

_app = None
_ui  = None
_design = None

runfrommenu = True

# Global set of event handlers to keep them referenced for the duration of the command
_handlers = []
_ms = []

PI = 3.14159265359

class MotherShip:
    def __init__(self):
#         """ This is just to clear bad globals that I shouldn't keep between 
#         different runs. It is NOT a solution, mostly laziness, 
 #        but since the structure of some objects is not entirely clear just yet,
 #        I don't dare doing more than this. """
        self.rowNumber = 0
        self.elnum = 0
        self.oldrow = -1        
        #damn globals! 
        self.jtctrl = None
        self.lastjoint = None
        self.packagename = 'mypackage'
        self.numoflinks = -1
        self.numofjoints = -1
        self.thistree = UrdfTree()
        
class UrdfTree:
    def __init__(self):
        self.elementsdict = {}
        self.currentel = None
        #self.placedlinks = []

    def addLink(self, linkname,linknum):
        thislink = Link(linkname,linknum) 
        self.elementsdict.update({linknum:thislink})
        
    def addJoint(self, jointname,jointnum):
        thisjoint = Joint(jointname,jointnum) 
        self.elementsdict.update({jointnum:thisjoint})
        
    def rmElement(self,linknumstr):
        linknum = int(linknumstr)
        logging.debug('deleted element' + str(linknum)+ 'named: '+ self.elementsdict[linknum].name)
        self.elementsdict.pop(linknum)
        global _ms      
        _ms.rowNumber -=1
        #logging.warn('this is not properly implemented. results are unpredictable after this operation!')
        
    def _gentreefindbase(self, thiselementsdict, report):
        placedlinks = {}
        foundbase = False
        for el in self.elementsdict:
            if 'isLink' in dir(self.elementsdict[el]) and self.elementsdict[el].isLink and self.elementsdict[el].name == 'base':
                foundbase = True
                msg = 'found my base when testing. base is on row' + str(self.elementsdict[el].row)
                logging.debug(msg)
                report += msg +'\n'
                ### base is zero, so its coordinate system is correctly set, we just need to change the isset property
                self.elementsdict[el].coordinatesystem.isset = True
                ### adding base to placedlink list
                placedlinks.update({0:self.elementsdict[el]})
                assert placedlinks[0].coordinatesystem.isset
                thiselementsdict.pop(el)
                break
        if not foundbase:
            report += 'did not find base!' +'\n'
            logging.error('did not find base! the root link should have this name or a proper tree cannot be build. error ')
        return placedlinks, thiselementsdict, report
        
    def gentree(self):

        #report = ''
        #thiselementsdict = deepcopy(self.elementsdict)
        thiselementsdict = {}

        for el in self.elementsdict:
            thiselementsdict.update({el:self.elementsdict[el]})
            #### i am going to use this opportunity to check if links have a group
            if 'isLink' in dir(self.elementsdict[el]) and self.elementsdict[el].isLink:
                if not self.elementsdict[el].group:
                    report = 'found an empty group. virtual links are currently not supported. this will fail to build correct urdf!'
                    logging.error(report)
                    _ui.messageBox(report) ### or i could have used assert and did it all in one line...

        placedlinks, thiselementsdict, report = self._gentreefindbase(thiselementsdict, '')
        assert placedlinks[0].coordinatesystem.isset
        
        something = True
        while something:
            placedjoints, placedeldic, thiselementsdict, myrep =  self._findjoints(placedlinks, thiselementsdict)
            report += myrep
            if placedjoints:
                thiselementsdict, placedeldic, myrep = self._gentreecore(placedjoints, thiselementsdict, placedeldic)
                report += myrep
            else:
                something = False
                if thiselementsdict: ### after finishing this, thiseldict should be empty, if it isn't we have disconnected joints or links. 
                    message = str(len(thiselementsdict)) + ' floating elements found. This tree is not correct, please review your work!'
                    report += message
                    logging.warn(message)
                
        _ui.messageBox(report+'\n')
        logging.debug( str(placedeldic)+'\n'+str(self.elementsdict))
        
        ### placedeldic should have a sequence of joints and links that are not a tree, but close looking to it, 
        ### i forgot to set the link's parent joint, needed to remove the offset. but it should be easy to find it now. 
            

            
    def _gentreecore(self, placedjoints, thiselementsdict, placedeldic):
               #nextlinkstoplace = []       
        report = ''
        for joint in placedjoints:
            #nextlinkstoplace.append(joint.childlink)
            stillmerging = True
            while stillmerging:
                stillmerging, placedjoints, thiselementsdict, placedeldic, report = self._gentreecorecore(placedjoints, thiselementsdict, placedeldic, report, joint)                  
                    
        return thiselementsdict, placedeldic, report
        
        
    def _gentreecorecore(self, placedjoints, thiselementsdict, placedeldic, report, joint):
        stillmerging = False
        for el in thiselementsdict:
                if 'isLink' in dir(thiselementsdict[el]) and thiselementsdict[el].isLink and thiselementsdict[el].name == joint.childlink:
                    ### if childlink in placedeldic then it is a closed chain!
                    ### add it to placed elements
                    placedeldic.update({len(placedeldic):thiselementsdict[el]})
                    ### add placed links to report
                    report += 'placed a link named:' +thiselementsdict[el].name + ' because joint named:' + joint.name + ' told me to!\n'
                    ### need to set this joint as father of link thiselementsdict[el], but not on this reduced dictionary we are iterating, but on the main dic: self.elementsdict, which will be used to generate the urdf
                    self._genfatherjoint(thiselementsdict[el].name, joint)
                    ## pop it from this elements dict out of the loop (see couple of lines below)
                    stillmerging = True
                    break
        if stillmerging:
            thiselementsdict.pop(el) # here!
        return stillmerging, placedjoints, thiselementsdict, placedeldic, report
                            
                            
    def _genfatherjoint(self, linkname, joint):
        for el in self.elementsdict:
            if self.elementsdict[el].name == linkname:
                ### found my link
                self.elementsdict[el].genfatherjoint(joint)

    def _findjointscore(self, placedeldic, thiselementsdict):
        _,_, allplacedlinks = self._allLinks( placedeldic)
        
        myjoint = None
        el = None
        for el in thiselementsdict:
            if 'isJoint' in dir(thiselementsdict[el]) and thiselementsdict[el].isJoint:
            ### here is the place to look for whether parent and child are flipped. I will not do it, I will assume the person creating the thing is smart
            ### i can also check for closed loops as well (but that would be harder...)
                if thiselementsdict[el].parentlink in allplacedlinks:
                    myjoint = thiselementsdict[el]                
                    #### actually this may seem like a rather weird way to do this, but I don't want to recode this function
                    for elel in placedeldic:
                        if thiselementsdict[el].parentlink == placedeldic[elel].name:
                            ### then placedeldic[elel] is my link
                            ### if i did this correctly, the father link will already have a set coordinatesystem
                            logging.debug('placed link is ' + placedeldic[elel].name)
                            assert placedeldic[elel].coordinatesystem.isset                          

                            myjoint.setrealorigin(placedeldic[elel].coordinatesystem)
                    break
        return myjoint, el     
    
    def _findjoints(self, placedeldic, thiselementsdict):
        foundjoints = []
        something = True        
        report = ''
        while something:
            joint, eltopop = self._findjointscore(placedeldic, thiselementsdict)
            if joint is None:
                something = False
            else:
                foundjoints.append(joint)
                thiselementsdict.pop(eltopop)
                placedeldic.update({len(placedeldic):joint})
                report += 'placed joint:'+ joint.name + '\n'
        return foundjoints, placedeldic, thiselementsdict, report

        
    def _allLinks(self,whicheldict):
        exstr = ''
        nolinks = True
        alllinks = []
        alllinknames = []
        for el in whicheldict:
            if 'isLink' in dir(whicheldict[el]) and whicheldict[el].isLink:
                exstr = exstr +'link: ' + whicheldict[el].name + '\n'
                alllinknames.append(whicheldict[el].name)
                alllinks.append(whicheldict[el])
                nolinks = False
        if nolinks:
            exstr = 'no links!'
        return exstr,alllinks, alllinknames
        
    def allLinks(self):
        exstr,alllinks,_ = self._allLinks(self.elementsdict)
        return exstr,alllinks
        
    def allJoints(self):
        exstr,alljoints,_ = self._allJoints(self.elementsdict)
        return exstr,alljoints
        
    def _allJoints(self,  selfelementsdict):        
        exstr = ''
        nojoints = True
        alljoints = []
        alljointnames = []
        for el in selfelementsdict:
            if 'isJoint' in dir(selfelementsdict[el]) and selfelementsdict[el].isJoint:
                exstr = exstr +'joint: ' + selfelementsdict[el].name + '\n'
                alljoints.append(selfelementsdict[el])
                alljointnames.append( selfelementsdict[el].name)
                nojoints = False
        if nojoints:
            exstr = 'no joints!'
        return exstr,alljoints, alljointnames
        
    def allElements(self):
        exstr = ''
        noels = True
        allels = []
        for el in self.elementsdict:
            if 'isJoint' in dir(self.elementsdict[el]) and self.elementsdict[el].isJoint:
                namename = 'joint: '
            elif 'isLink' in dir(self.elementsdict[el]) and self.elementsdict[el].isLink:
                namename = 'link: '
            else:
                namename = 'unk: '
            exstr = exstr + namename + self.elementsdict[el].name + '\n'
            allels.append(self.elementsdict[el])
            noels = False
        if noels:
            exstr = 'no elements!'
        return exstr,allels
        
    def getel(self,selected):
        logging.debug('selected' + str(selected))
        logging.debug('len...' + str(len(self.elementsdict)))
        if selected not in self.elementsdict:
            return None
        else:
            logging.debug('dic...' + str(self.elementsdict))
            ## is it in the dict though?
            return self.elementsdict[selected]
    def getcurrenteldesc(self):
        if self.currentel is None:
            return 'No current element'
        else:
            return self.currentel.name +'\n' + self.currentel.getitems()
        
    def setcurrentel(self,crnum):
        thisel = self.getel(crnum)
        if thisel is not None:
            self.currentel = thisel
        

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
        #self.xyz = '0 0 0'
        #self.rpy = '0 0 0'
        #self.x = 0
        #self.z = 0
        #self.y = 0
        #self.r = 0
        #self.p = 0
        #self.yaw = 0
        self.setxyz(0,0,0)
        self.setrpy(0,0,0)        
        
        self.isset = False
    def setxyz(self,x,y,z):
        self.isset = True
        self.xyz = str(x/100)+' ' + str(y/100)+' ' + str(z/100) ### the internal representation of joint occurrences offsets seems to be in cm no matter what you change the units to be. this needs to be checked, but i think it is always like this. if you are reading this line and wondering if this is the reason why your assembly looks like it exploded, then I was wrong...
        ### there will be inconsistencies here and if you change the values below to be "right", then the translation part on .genlink will not work. be mindful when trying to fix it. 
        self.x = x
        self.y = y
        self.z = z
    def setrpy(self,r,p,y):
        self.rpy = str(r/180*PI)+' ' + str(p/180*PI)+' ' + str(y/180*PI) 
        #TODO: this maybe not the right conversion constant!!!!!!!!!!        
        self.r = r
        self.p = p
        self.yaw = y
        
                
        
class SixDegree(OrVec):
    #TODO: need to link it to actual joint and link orvec, probably will change the class orvec and instantiate the call form the link and joint objects to have them linked 
    #TODO: need to initialize this with actual OrVec self values and change OrVec values in the interact portion. 
    def __init__(self):
        super().__init__()
                
    def setxyzrpy(self,inputs):
        distanceValue1Input = inputs.itemById('distanceValueX')
        distanceValue2Input = inputs.itemById('distanceValueY')
        distanceValue3Input = inputs.itemById('distanceValueZ')
        angleValue1Input = inputs.itemById('angleValueRoll')
        angleValue2Input = inputs.itemById('angleValuePitch')
        angleValue3Input = inputs.itemById('angleValueYaw')                
                
        distanceValue1Input.value = self.x
        distanceValue2Input.value = self.y
        distanceValue3Input.value = self.z
        angleValue1Input.value = self.r
        angleValue2Input.value = self.p
        angleValue3Input.value = self.yaw
        angleValue1Input.setManipulator(adsk.core.Point3D.create(distanceValue1Input.value, distanceValue2Input.value, distanceValue3Input.value), adsk.core.Vector3D.create(0, 1, 0), adsk.core.Vector3D.create(0, 0, 1))
        angleValue2Input.setManipulator(adsk.core.Point3D.create(distanceValue1Input.value, distanceValue2Input.value, distanceValue3Input.value), adsk.core.Vector3D.create(0, 0, 1), adsk.core.Vector3D.create(1, 0, 0))
        angleValue3Input.setManipulator(adsk.core.Point3D.create(distanceValue1Input.value, distanceValue2Input.value, distanceValue3Input.value), adsk.core.Vector3D.create(1, 0, 0), adsk.core.Vector3D.create(0, 1, 0))
                
        
    def interact(self,inputs):        
        distanceValue1Input = inputs.itemById('distanceValueX')
        distanceValue2Input = inputs.itemById('distanceValueY')
        distanceValue3Input = inputs.itemById('distanceValueZ')
        angleValue1Input = inputs.itemById('angleValueRoll')
        angleValue2Input = inputs.itemById('angleValuePitch')
        angleValue3Input = inputs.itemById('angleValueYaw')                
        
        self.x = distanceValue1Input.value 
        self.y = distanceValue2Input.value
        self.z = distanceValue3Input.value 
        self.r = angleValue1Input.value
        self.p = angleValue2Input.value 
        self.yaw = angleValue3Input.value       
        
    def jointset(self):
        self.isset = True

def chcontrols(inputs,allvisible,allenabled):
        
        distanceValue1Input = inputs.itemById('distanceValueX')
        distanceValue2Input = inputs.itemById('distanceValueY')
        distanceValue3Input = inputs.itemById('distanceValueZ')
        angleValue1Input = inputs.itemById('angleValueRoll')
        angleValue2Input = inputs.itemById('angleValuePitch')
        angleValue3Input = inputs.itemById('angleValueYaw')                
                
        distanceValue1Input.isVisible = allvisible
        distanceValue1Input.isEnabled = allenabled       

        distanceValue2Input.isVisible = allvisible
        distanceValue2Input.isEnabled = allenabled       

        distanceValue3Input.isVisible = allvisible
        distanceValue3Input.isEnabled = allenabled       

        angleValue1Input.isVisible = allvisible
        angleValue1Input.isEnabled = allenabled          

        angleValue2Input.isVisible = allvisible
        angleValue2Input.isEnabled = allenabled       
 
        angleValue3Input.isVisibile = allvisible
        angleValue3Input.isEnabled = allenabled
        
class Visual:
    def __init__(self):
        self.origin = OrVec()
        self.geometryfilename = ""
        self.materialname = ""
        self.color = '0.792156862745098 0.819607843137255 0.933333333333333 1' ### the colour that was being used in our other files. i am used to it, so i will keep it

class Collision:
    def __init__(self):
        self.origin = OrVec()
        self.geometryfilename = ""

class Link:
    def __init__(self,occname,row):
        parent = '' ### incorrect, we need to parse the fullPathName, which should be the way to instantiate this as well!
        #### actually, since i've changed this structure so much, now is not the time to try to set this things correctly...
        level = 0
        self.inertial = Inertial()
        self.visual = Visual()
        self.collision = Collision();
        self.level = level
        self.name = parent+ occname;
        self.visual.geometryfilename = ""
        self.collision.geometryfilename = ""
        self.group = []
        self.isLink = True
        self.row = row
        self.coordinatesystem = OrVec()
        self.isVirtual = True
    def __groupmembers(self,rigidgrouplist):
        self.group = rigidgrouplist.getgroupmemberships(self.name)
        return rigidgrouplist.getwholegroup(self.name)
        
    def getitems(self):
        items = ''
        for el in self.group:
            items = items + el.name + '\n'
        return items
        
    def genfatherjoint(self,joint):
        if not joint.isset:
            logging.error('tried to set displacement for link:' +self.name + ',but joint ' + joint.name + ' is not set.')
        ### need to set the self.coordinatesystem to contain at least the displacement from the joint. 
        ### rotations are also probably important, but i will not do that for now. 
        else:
            self.coordinatesystem = joint.origin
        
    def makexml(self, urdfroot):
        self.visual.geometryfilename = "package://"+_ms.packagename+"/meshes/" + clearupst(self.name) +".stl"

        link = etree.SubElement(urdfroot, "link", name= clearupst(self.name))

        if not self.isVirtual:        
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
            #### my asserts to try to avoid crashing etree
            assert type(self.inertial.origin.xyz) == str
            assert type(self.inertial.origin.rpy) == str
            assert type(self.inertial.mass) == str
            assert type(self.inertial.inertia.ixx) == str
            assert type(self.inertial.inertia.ixy) == str
            assert type(self.inertial.inertia.ixz) == str
            assert type(self.inertial.inertia.iyy) == str
            assert type(self.inertial.inertia.iyz) == str
            assert type(self.inertial.inertia.izz) == str
            assert type( self.visual.origin.xyz) == str
            assert type(self.visual.origin.rpy ) == str
            assert type( self.visual.geometryfilename) == str
            assert type(self.visual.materialname) == str
            assert type(self.visual.color) == str
            assert type(self.collision.origin.xyz) == str
            assert type(self.collision.origin.rpy) == str
            assert type(self.visual.geometryfilename) == str
            #assert type(a) == str
            #assert type(a) == str
        return urdfroot
        

    def genlink(self,meshes_directory, components_directory):
        didifail = 0        
        self.isVirtual = False
        try:            
            logging.debug('starting genlink')
            # Get the root component of the active design
            rootComp = _design.rootComponent
    
            # Create two new components under root component
            allOccs = rootComp.allOccurrences                    
            
            # create a single exportManager instance
            exportMgr = _design.exportManager
            
            ###TODO: this needs to be done for the joints as well. aff...
            removejointtranslation = adsk.core.Matrix3D.create()
            translation = adsk.core.Vector3D.create(-self.coordinatesystem.x, -self.coordinatesystem.y, -self.coordinatesystem.z)
            removejointtranslation.setToIdentity()
            removejointtranslation.translation = translation
            logging.debug('Offset from joint is:' + str( removejointtranslation.asArray()))
            
            #### add occurrances from other stuff to this new stuff
            for i in range(0,len(self.group)):
                #express = 'it'+str(i)+ '=self.group[i].transform.copy()'
                pathsplit = self.group[i].fullPathName.split('+')                

                newrotl = []
                for j in range(1,len(pathsplit)):                 
                    thisoccnamelist = pathsplit[0:j]
                    thisoccname = thisoccnamelist[0]
                    for k in range(1,len(thisoccnamelist)):
                        thisoccname = thisoccname + '+' + thisoccnamelist[k]
                    logging.info('getting the tm for:'+thisoccname)
                    for l in range(0,allOccs.count):
                        if allOccs.item(l).fullPathName == thisoccname:
                            #then i want to multiply their matrices!
                            lasttm = allOccs.item(l).transform.copy()
                            newrotl.append(lasttm)
                            logging.debug(allOccs.item(l).fullPathName)
                            logging.debug('with tm:' + str(lasttm.asArray()))
                            #newrot.transformBy(allOccs.item(l).transform)
                    ### now that i have all the occurrences names i need to get them from allOccs(?!)
                lasttransform = self.group[i].transform.copy()
                
                newrotl.append(lasttransform)
                
#                newrot = removejointtranslation

                newrot = adsk.core.Matrix3D.create()
                newrot.setToIdentity()

                for j in reversed(range(0,len(newrotl))):
                    newrot.transformBy(newrotl[j])
                newrot.transformBy(removejointtranslation)
                express = 'it'+str(i)+ '=newrot'
                exec(express)
            
            
            #stlname = rootComp.name.translate(None, ':!@#$')
            #line = re.sub('[!@#$]', '', line)
            stlname = clearupst(self.name)
            
            #fileName = components_directory+'/' + stlname
            for i in range(0,len(self.group)):
                # export the root component to printer utility
                fileName = components_directory+'/' + stlname+str(i)
                logging.info('saving file '+fileName )
                logging.info('from occurrence' + self.group[i].fullPathName)
                
                logging.debug('with tm:' + str(eval('it'+str(i)+'.asArray()')))
                stpOptions = exportMgr.createSTEPExportOptions(fileName, self.group[i].component)           
                exportMgr.execute(stpOptions)
                
            # Create a document.
            doc = _app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
            doc.name = self.name
            
            product = _app.activeProduct
            design = adsk.fusion.Design.cast(product)
            
            # Get the root component of the active design
            rootComp = design.rootComponent
            
            #### i need to divide it by 1000, actually transform it from whatever unit the original drawing was on, into SI, i.e. meters, since that is what rviz and ros use. I will do this using another transformation:
#            mytransf = adsk.core.Matrix3D.create()
#            mytransf.setToIdentity()
#            global thisdocsunits
#            if thisdocsunits == "mm":
#                myscaleratio = 1/1000
#            elif thisdocsunits == "cm":
#                myscaleratio = 1/100
#            mytransf.setCell(1,1,myscaleratio)
#            mytransf.setCell(2,2,myscaleratio)
#            mytransf.setCell(3,3,myscaleratio)
            ###turns out this a nonuniform transform and fusion has a check against letting you do this. i can't turn it off, or so it seems

    
            # Create two new components under root component
            allOccs = rootComp.occurrences   
            
            # Get import manager
            importManager = _app.importManager            
            
            #### add occurrances from other stuff to this new stuff
            for i in range(0,len(self.group)):
                fileName = components_directory+'/' + stlname+str(i)+'.stp'
                logging.info('loading file: '+fileName)
                stpOptions = importManager.createSTEPImportOptions(fileName)
                importManager.importToTarget(stpOptions, rootComp)
            for i in range(0,len(rootComp.occurrences)):
                thistransf = eval('it'+str(i))
                ## i also want to scale them to SI units. doing it here is easier
                #thistransf.transformBy(removejointtranslation)    
                rootComp.occurrences.item(i).transform = thistransf
                #rootComp.occurrences.item(i).transform = eval('it'+str(i))
                pass
            
            ###TODO:
            ### must set mass and center of inertia! i think visual and origins are correct because this info is in the stl...
            logging.info('XYZ moments of inertia:'+str(rootComp.physicalProperties.getXYZMomentsOfInertia()))
            logging.info('Mass:'+str(rootComp.physicalProperties.mass))
            
            ### setting units to meters so stls will have proper sizes!
            unitsMgr = design.fusionUnitsManager

            unitsMgr.distanceDisplayUnits = adsk.fusion.DistanceUnits.MeterDistanceUnits
            
            # create aNOTHER! exportManager instance
            exportMgr = design.exportManager

            # export the root component to printer utility
            stlRootOptions = exportMgr.createSTLExportOptions(rootComp,  meshes_directory+'/' + stlname)
    
            # get all available print utilities
            #printUtils = stlRootOptions.availablePrintUtilities
    
            # export the root component to the print utility, instead of a specified file
            #for printUtil in printUtils:
            #    stlRootOptions.sendToPrintUtility = True
            #   stlRootOptions.printUtility = printUtil
            stlRootOptions.sendToPrintUtility = False
            logging.info('saving STL file: '+ meshes_directory+'/' + stlname )
            exportMgr.execute(stlRootOptions)            
            
            self.visual.geometryfilename = "package://"+_ms.packagename+"/meshes/" + stlname +".stl"
            self.collision.geometryfilename = self.visual.geometryfilename # the legend has it that this file should be a slimmer version of the visuals, so that collisions can be calculated more easily....       
    
        except:
            logging.debug('could not save stl. {}'.format(traceback.format_exc()))
            didifail = 1
        return didifail
        
class Joint:
    # jointdefs = Joint(actualjoint, actualjointname,parentl,childl, currentLevel,parent);
    def __init__(self,jointname,row):
        level= 0
        self.name = jointname
        self.generatingjointname = ''
        self.origin = SixDegree() 
        #self.origin = OrVec()

        self.realorigin = OrVec()
        self.parentlink = ''
        self.childlink = ''
        self.axis = '0 0 0'
        self.limit = Limit()
        self.level = level
        self.type = ''
        self.row = row # i am not sure why i am savign this...
        self.isJoint = True
        self.isset = False
        self.entity = None ## this will have the whole joint that created this joint instance. sort of dumb, but it is the way I can repopulate the selections... 
    def setjoint(self,joint,cmdInputid,inputs):#,parentl,childl):
        self.isset = True
        self.generatingjointname = joint.name
        self.entity = joint ### i need this to repopulate selection, but I know it might break the code even more...
        
        ### TODO: REVIEW THIS!
        #self.origin.interact(cmdInputid,inputs) # this can maybe happen only if setxyz fails(?) 

        #self.parentlink = parentl
        #self.childlink = childl
        
        #==============================================================================
        #         python doesnt have a switch statement, i repeat python does not have a switch statement...
        #         from the docs, we should implement this:
        #         Name     Value     Description
        #         BallJointType     6     Specifies a ball type of joint.
        #         CylindricalJointType     3     Specifies a cylindrical type of joint.
        #         PinSlotJointType     4     Specifies a pin-slot type of joint.
        #         PlanarJointType     5     Specifies a planar type of joint.
        #         RevoluteJointType     1     Specifies a revolute type of joint.
        #         RigidJointType     0     Specifies a rigid type of joint.
        #         SliderJointType     2     Specifies a slider type of joint.
        #==============================================================================
        try:
            self.origin.setxyz(joint.geometryOrOriginOne.origin.x, joint.geometryOrOriginOne.origin.y, joint.geometryOrOriginOne.origin.z)
            self.origin.setxyzrpy(inputs)
        except:
            try:
                self.origin.setxyz(joint.geometryOrOriginTwo.origin.x, joint.geometryOrOriginTwo.origin.y, joint.geometryOrOriginTwo.origin.z)
                self.origin.setxyzrpy(inputs)
            except:                        
                _ui.messageBox('Could not set joint origin. This will affect the whole assembly and it will be hard to fix!!! This is quite possibly a bug in the API. {}'.format(traceback.format_exc()))
                logging.error('Could not set joint origin. This is quite possibly a bug in the API. {}'.format(traceback.format_exc()))
            ### TODO so I am not using the base occurrences to set this joint - i am not using .geometryOrOriginTwo for anythin - so I might be making mistakes in prismatic joints - who uses those??? - so I should check to see if they are same and warn at least in case they are not...
                logging.warn('Could not set joint origins for joint: ' + self.name+'. You need to edit the URDF and fix it manually.')

        try:
            if joint.jointMotion.jointType is 1:
                self.type = "revolute"
                self.axis = str(joint.jointMotion.rotationAxisVector.x)+ ' ' + str(joint.jointMotion.rotationAxisVector.y)+ ' ' + str(joint.jointMotion.rotationAxisVector.z)
            if joint.jointMotion.jointType is 0:
                self.type = "fixed"
            
            haslimits = False
            if 'rotationLimits' in dir(joint.jointMotion):
                if joint.jointMotion.rotationLimits.isMinimumValueEnabled:
                    self.limit.lower = str(joint.jointMotion.rotationLimits.minimumValue)
                    haslimits = True
                if joint.jointMotion.rotationLimits.isMaximumValueEnabled:
                    self.limit.upper = str(joint.jointMotion.rotationLimits.maximumValue)
                    haslimits = True
            if self.type == "revolute" and not haslimits:
                self.type = "continuous"
        except:
            self.type = "fixed" ## i still want to produce some sort of URDF. hopefully this will be a bad one, but recoverable by changing offsets and joint type/angles
            logging.debug('could not set joint type or limits. Setting it to fixed. This is quite possibly a bug in the API. {}'.format(traceback.format_exc()))
            _ui.messageBox('could not set joint type or limits. Setting it to fixed. This is quite possibly a bug in the API. {}'.format(traceback.format_exc()))
            logging.warn('Could not set joint type for joint' + self.name+'. You need to edit the URDF and fix it manually.')

    def setrealorigin(self, fathercoordinatesystem):
        assert fathercoordinatesystem.isset
        self.realorigin.setxyz(self.origin.x- fathercoordinatesystem.x, self.origin.y - fathercoordinatesystem.y, self.origin.z- fathercoordinatesystem.z)
            
    def getitems(self):
        items = 'genjn:'+self.generatingjointname+'\n'+'parent:' + self.parentlink + '\t' + 'child:' + self.childlink        
        return items

    def makexml(self, urdfroot):

        joint = etree.SubElement(urdfroot, "joint", name= clearupst(self.name), type = self.type)
        etree.SubElement(joint, "origin", xyz = self.realorigin.xyz, rpy = self.realorigin.rpy)
        etree.SubElement(joint, "parent", link = self.parentlink)
        etree.SubElement(joint, "child", link = self.childlink)
        etree.SubElement(joint, "axis", xyz = self.axis)
        etree.SubElement(joint, "limit", lower = self.limit.lower, upper = self.limit.upper, effort=self.limit.effort, velocity = self.limit.velocity)
        #origin = etree.SubElement(inertial, "origin")
        #etree.SubElement(origin, "xyz").text = self.inertial.origin.xyz
        #etree.SubElement(origin, "rpy").text = self.inertial.origin.rpy
        ###my asserts checks now, because this code is driving me insane
        assert type(self.type) == str        
        assert type(self.realorigin.xyz) == str
        assert type(self.realorigin.rpy) == str
        assert type(self.parentlink) == str
        assert type(self.childlink) == str
        assert type(self.axis) == str
        assert type(self.limit.lower) == str
        assert type(self.limit.upper) == str
        assert type(self.limit.effort) == str
        assert type( self.limit.velocity) == str        
        
        return urdfroot
        
class Limit:
    def __init__(self):
        self.lower = '-1'
        self.upper = '1'
        self.effort = '0'
        self.velocity = '0'
        
def superprint(level,stringo):
    #logger = logging.getLogger(__name__)
    #logger.debug(spaces(level*5)+stringo)
    logging.debug(spaces(level*5)+stringo)


def clearupst(stringo):
    strstr1 = re.sub('[:!@#$.()/-]', '',stringo)
    strstr2 = re.sub(' ', '_',strstr1)
    return strstr2

# Returns a string containing the especified number of spaces.
def spaces(spaceCount):
    result = ''
    for i in range(0, spaceCount):
        result += ' '

    return result


# Adds a new row to the table.
def addRowToTable(tableInput,LinkOrJoint):
    global _ms
    # Get the CommandInputs object associated with the parent command.
    cmdInputs = adsk.core.CommandInputs.cast(tableInput.commandInputs)
    
    if LinkOrJoint =='' or LinkOrJoint == 'Link':
        dropdownthingy = True
        _ms.numoflinks += 1
    elif LinkOrJoint =='Joint':
        dropdownthingy = False        
        _ms.numofjoints += 1
    
    # Create three new command inputs.
    #valueInput = cmdInputs.addTextBoxCommandInput('TableInput_value{}'.format(_ms.elnum ), 'JorL', 'Link',1,True)
    JorLInput = cmdInputs.addDropDownCommandInput('TableInput_value{}'.format(_ms.elnum ), 'JorLTable{}'.format(_ms.elnum ), adsk.core.DropDownStyles.TextListDropDownStyle)
    dropdownItems = JorLInput.listItems
    dropdownItems.add('Link', dropdownthingy, '')
    dropdownItems.add('Joint', not dropdownthingy,'')   
    if _ms.elnum  == 0:
        rightlinkname = 'base'        
    elif LinkOrJoint =='' or LinkOrJoint == 'Link':
        rightlinkname = 'link' +str(_ms.numoflinks) # str(_ms.elnum )
    elif LinkOrJoint =='Joint':
        rightlinkname = 'joint' + str(_ms.numofjoints)# str(_ms.elnum )
        
    stringInput =  cmdInputs.addStringValueInput('TableInput_string{}'.format(_ms.elnum ), 'StringTable{}'.format(_ms.elnum ), rightlinkname)
    elnnumInput =  cmdInputs.addStringValueInput('elnum{}'.format(_ms.elnum ), 'elnumTable{}'.format(_ms.elnum ), str(_ms.elnum ))
    #spinnerInput = cmdInputs.addIntegerSpinnerCommandInput('spinnerInt{}'.format(_ms.elnum ), 'Integer Spinner', 0 , 100 , 2, int(_ms.elnum ))
    slbutInput = cmdInputs.addBoolValueInput('butselectClick{}'.format(_ms.elnum ),'Select',  False,'', True)
 
    
    
    elnnumInput.isEnabled = False
    stringInput.isEnabled = False ##### i~m disabling the ability to change element~s name randomly...
    # Add the inputs to the table.
    row = tableInput.rowCount
    ha0 = tableInput.addCommandInput( elnnumInput, row, 0)
    ha1 = tableInput.addCommandInput(JorLInput, row, 1)
    #tableInput.addCommandInput(valueInput, row, 0)
    ha2 = tableInput.addCommandInput(stringInput, row, 2)
    #tableInput.addCommandInput(spinnerInput, row, 2)
    ha3 = tableInput.addCommandInput(slbutInput, row, 3)
    
    print(ha0)
    print(ha1)    
    print(ha2)
    print(ha3)
    
    # Increment a counter used to make each row unique.

    _ms.rowNumber = _ms.rowNumber + 1
    _ms.elnum  += 1
    

# Event handler that reacts to any changes the user makes to any of the command inputs.
class AddLinkCommandInputChangedHandler(adsk.core.InputChangedEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            global _ms
            
            eventArgs = adsk.core.InputChangedEventArgs.cast(args)
            inputs = eventArgs.inputs
            cmdInput = eventArgs.input
            
            #linkInput = inputs.itemById('linkname')
            JorLNameInput = inputs.itemById('StringTable')

            tableInput = inputs.itemById('table')
            debugInput = inputs.itemById('debugbox')
            linkgroupInput = inputs.itemById('linkgroup')
            jointgroupInput = inputs.itemById('jointgroup')
            
            if linkgroupInput is None: ###inside the group, there is no group!
                linkselInput = inputs.itemById('linkselection') 
            else:
                linkselInput = linkgroupInput.children.itemById('linkselection') 
            
            if jointgroupInput is None: ###inside the group, there is no group!
                jointselInput = inputs.itemById('jointselection') 
            else:
                jointselInput = jointgroupInput.children.itemById('jointselection')             
            
#            if _ms.thistree.currentel is not None:
#                _ms.oldrow = _ms.thistree.currentel.row
#            else:
#                _ms.oldrow = -1
                
   
            
            if tableInput is not None:
                ################################################################
                # set current link
                ### if working in table contextÇ otherwise we do not want to change it.
                if tableInput.selectedRow == -1:
                    ### it means we have nothing selecte, so we don~t want to change anything
                    pass
                else:
                    elementtobedefined = tableInput.getInputAtPosition(tableInput.selectedRow,0).value                
                    setcurrel(elementtobedefined,debugInput, _ms.oldrow, linkselInput, jointselInput)
                
#                crnum = getrow('TableInput_value', cmdInput.id, tableInput.selectedRow,debugInput)
#                if crnum and tableInput.selectedRow != -1 and tableInput.getInputAtPosition(tableInput.selectedRow,1).selectedItem.name == 'Joint' and tableInput.getInputAtPosition(tableInput.selectedRow,1).isEnabled:
#                    tableInput.getInputAtPosition(tableInput.selectedRow,2).value = 'joint'+crnum
    
                    #JorLTableInput
                    ### if it is different from what it was before, then i should change the name, right?
                    #_ui.messageBox('changedstuff! in row' + rowrow)
                crnum = getrow('butselectClick', cmdInput.id, tableInput,debugInput)
                if crnum:
                    if tableInput.selectedRow == -1:
                        ### it means we have nothing selected, so we don~t want to change anything
                        pass
                    else:
                        elementtobedefined = tableInput.getInputAtPosition(tableInput.selectedRow,0).value                
                        setcurrel(elementtobedefined,debugInput, _ms.oldrow, linkselInput, jointselInput)
                        #### it was getting complicated for me to debug this, so i am simpliflying the UI. i will only be able to change the name of the selected link. that's it. 
                        #### i know clicking it changes the row - this doesn~t happen so nicely with the string, so i will use this
                        tableInput.getInputAtPosition(tableInput.selectedRow,2).isEnabled = True
                        if _ms.oldrow != -1 and _ms.oldrow != tableInput.selectedRow:
                            tableInput.getInputAtPosition(_ms.oldrow,2).isEnabled = False
                        
#                if cmdInput.id == 'tableCreate' and  tableInput.getInputAtPosition(tableInput.selectedRow,1).isEnabled:           
#    
#                    tableInput.getInputAtPosition(tableInput.selectedRow,1).isEnabled = False
#                    ### and create stuff!!!
#                    if tableInput.getInputAtPosition(tableInput.selectedRow,1).selectedItem.name == 'Link':
#                        linkname = tableInput.getInputAtPosition(tableInput.selectedRow,2).value
#                        logging.debug('adding link:' + str(linkname))
#                        _ms.thistree.addLink(linkname,tableInput.selectedRow)
#                        setcurrel(tableInput.selectedRow,debugInput, oldrow, linkselInput, jointselInput)
#                    elif tableInput.getInputAtPosition(tableInput.selectedRow,1).selectedItem.name == 'Joint':
#                        jointname = tableInput.getInputAtPosition(tableInput.selectedRow,2).value
#                        logging.debug('adding joint:' + str(jointname))
#                        _ms.thistree.addJoint(jointname,tableInput.selectedRow)
#                        setcurrel(tableInput.selectedRow,debugInput, oldrow, linkselInput, jointselInput)
                            
                crnum = getrow('TableInput_string', cmdInput.id, tableInput,debugInput)
                if crnum:
                    ####should change the name of the current element here

                    if tableInput.selectedRow == -1:
                        ### it means we have nothing selecte, so we don~t want to change anything
                        pass
                    else:
                        _ms.thistree.currentel.name =  tableInput.getInputAtPosition(tableInput.selectedRow,2).value
                        elementtobedefined = tableInput.getInputAtPosition(tableInput.selectedRow,0).value                
                        setcurrel(elementtobedefined,debugInput, _ms.oldrow, linkselInput, jointselInput)
                    
                
                if cmdInput.id == 'packagename':
                    pkgnInput = inputs.itemById('packagename')
                    _ms.packagename = pkgnInput.value
                    
                if cmdInput.id == 'tableJointAdd':
                    addRowToTable(tableInput,'Joint')
                    tableInput.getInputAtPosition(_ms.rowNumber-1,1).isEnabled = False
                    ####horrible hack because it is lateand i am tired of this thing.
                    logging.debug('adding joint. row number'+str(_ms.rowNumber))
                    jointname = tableInput.getInputAtPosition(_ms.rowNumber-1,2).value
                    logging.debug('adding joint:' + str(jointname))
                    _ms.thistree.addJoint(jointname,_ms.elnum -1)
                    #_ms.thistree.addJoint(jointname,_ms.elnum -1,inputs)
                    #setcurrel(tableInput.getInputAtPosition(tableInput.selectedRow,0).value,debugInput, oldrow, linkselInput, jointselInput)
                    
                if cmdInput.id == 'tableLinkAdd':
                    addRowToTable(tableInput,'Link')
                    tableInput.getInputAtPosition(_ms.rowNumber-1,1).isEnabled = False
                    logging.debug('adding link. row number'+str(_ms.rowNumber))
                    linkname = tableInput.getInputAtPosition(_ms.rowNumber-1,2).value
                    logging.debug('adding link:' + str(linkname))
                    _ms.thistree.addLink(linkname,_ms.elnum -1)
                    #setcurrel(tableInput.getInputAtPosition(tableInput.selectedRow,0).value,debugInput, oldrow, linkselInput, jointselInput)
                        
                if cmdInput.id == 'tableAdd':
                    addRowToTable(tableInput,'')
                elif cmdInput.id == 'tableDelete':
                    if tableInput.selectedRow == -1:
                        _ui.messageBox('Select one row to delete.')
                    else:
                        ###this only works if every element is created as well...
                        logging.debug('trying to delete element from row:' + str(tableInput.selectedRow) + ' supposedly index:' + tableInput.getInputAtPosition(tableInput.selectedRow,0).value)
                        elementnumbertoremove = tableInput.getInputAtPosition(tableInput.selectedRow,0).value
                        _ms.thistree.rmElement(elementnumbertoremove)
                        tableInput.deleteRow(tableInput.selectedRow)
                        
                ### setting up visibility of joint and link group selection stufffs:
                if tableInput.selectedRow!= -1 and not tableInput.getInputAtPosition(tableInput.selectedRow,1).isEnabled and  tableInput.getInputAtPosition(tableInput.selectedRow,1).selectedItem.name == 'Link':
                    
                    linkgroupInput.isVisible = True
                    jointgroupInput.isVisible = False
                    chcontrols(jointgroupInput.children,True,False)
                if tableInput.selectedRow!= -1 and not tableInput.getInputAtPosition(tableInput.selectedRow,1).isEnabled and  tableInput.getInputAtPosition(tableInput.selectedRow,1).selectedItem.name == 'Joint':
                    
                    linkgroupInput.isVisible = False
                    jointgroupInput.isVisible = True
                    
                    chcontrols(jointgroupInput.children,True,True)
                    #
                    assert _ms.thistree.currentel.isJoint
                    _ms.thistree.currentel.origin.setxyzrpy(jointgroupInput.children)

                    pln = jointgroupInput.children.itemById('parentlinkname')
                    cln = jointgroupInput.children.itemById('childlinkname')
                    alllinkstr, _ = _ms.thistree.allLinks()
                    alllinkgr = alllinkstr.split('\n')
                    pln.listItems.clear()
                    cln.listItems.clear()
                    for link in  alllinkgr:
                        pln.listItems.add(link, False,'')
                        cln.listItems.add(link, False,'')
                        
            if cmdInput.id == 'linkselection':
                #### wait, i think i can export a selection! so...
                #### so, if I try to select things without having set anything, it jumps here into linkselection. I don't want this to happen, so i will make it create a ballon to warn it
                if 'group' not in dir(_ms.thistree.currentel):
                    _ui.messageBox('Must create link or joint before selecting!')
                    return
                _ms.thistree.currentel.group = [] #### i refer to element, but i know it is a link!
                for i in range(0, linkselInput.selectionCount):
                    if linkselInput.selection(i).entity not in _ms.thistree.currentel.group:
                        logging.debug('adding link entity:'+ linkselInput.selection(i).entity.name)
                        _ms.thistree.currentel.group.append( linkselInput.selection(i).entity)
                        if "PRT" in linkselInput.selection(i).entity.name:
                            pass
                        ##TODO:
                        # REMOVE child occurrences that can be in the list, or they will be doubled in generating the link -> larger mesh, wrong weight and moments of inertia
                        #logging.debug(dir(linkselInput.selection(i).entity))
            if cmdInput.id == 'parentlinkname':
                pln = inputs.itemById('parentlinkname')
                aa= pln.selectedItem.name.split('link: ')
                _ms.thistree.currentel.parentlink = aa[1]
                
            if cmdInput.id == 'childlinkname':
                cln = inputs.itemById('childlinkname')
                aa= cln.selectedItem.name.split('link: ')
                _ms.thistree.currentel.childlink = aa[1]

            if cmdInput.id == 'jointselection' and jointselInput.selectionCount == 1:
               logging.debug('adding joint entity:'+ jointselInput.selection(0).entity.name)
               _ms.thistree.currentel.setjoint( jointselInput.selection(0).entity,cmdInput.id,inputs)
            
            if cmdInput.id == 'createtree':
                #linkselInput.hasFocus = True #### if this is not set, then you cannot click OK idk why...
                ### actually it is worse. if you don~t have a selection from the selection thing as active, it will not let you execute it.
                ### so horrible not realy a fix:                
                _ms.thistree.gentree()
                if linkselInput.selectionCount == 0 and jointselInput.selectionCount == 0:
                    _ui.messageBox("one last thing: if you leave both joint and link selections without any thing select, fusion will believe it does not need to execute the command - so the OK will be grayed out. Moreover, if it either of them have focus, but don't have anything selected, it will show the OK button, but it will not execute anything. i currently don't know how to fix this without either saving the selection and repopulating them each time the user clicks on the select button- maybe a nice feature, but something that will take me some time to do, or adding subcommands to do those selections - something I am not sure if it is possible (it should be), but also will take me some time to get around doing. \n easiest way to fix this is go to a joint and reselect it, then run OK")
                
            ###### joint control
            distanceValue1Input = inputs.itemById('distanceValueX')
            distanceValue2Input = inputs.itemById('distanceValueY')
            distanceValue3Input = inputs.itemById('distanceValueZ')
            
            angleValue1Input = inputs.itemById('angleValueRoll')
            angleValue2Input = inputs.itemById('angleValuePitch')
            angleValue3Input = inputs.itemById('angleValueYaw')
            
     
            if cmdInput.id == 'distanceValueY':            
                distanceValue3Input.setManipulator(adsk.core.Point3D.create(distanceValue1Input.value, distanceValue2Input.value, 0), adsk.core.Vector3D.create(0, 0, 1))
                #distanceValue3Input.manipulatorOrigin.y = distanceValue2Input.value
                
            if cmdInput.id == 'distanceValueZ':            
                #distanceValue2Input.setManipulator(adsk.core.Point3D.create(0, 0, 0), adsk.core.Vector3D.create(0, 1, 0))
                pass
            if cmdInput.id == 'distanceValueX':            
                #distanceValue2Input.setManipulator(adsk.core.Point3D.create(0, 0, 0), adsk.core.Vector3D.create(0, 1, 0))
                distanceValue2Input.setManipulator(adsk.core.Point3D.create(distanceValue1Input.value, 0, 0), adsk.core.Vector3D.create(0, 1, 0))
                distanceValue3Input.setManipulator(adsk.core.Point3D.create(distanceValue1Input.value, distanceValue2Input.value, 0), adsk.core.Vector3D.create(0, 0, 1))
        
       
            if cmdInput.id in ['distanceValueX','distanceValueY','distanceValueZ']:
                 
                angleValue1Input.setManipulator(adsk.core.Point3D.create(distanceValue1Input.value, distanceValue2Input.value, distanceValue3Input.value), adsk.core.Vector3D.create(0, 1, 0), adsk.core.Vector3D.create(0, 0, 1))
                angleValue2Input.setManipulator(adsk.core.Point3D.create(distanceValue1Input.value, distanceValue2Input.value, distanceValue3Input.value), adsk.core.Vector3D.create(0, 0, 1), adsk.core.Vector3D.create(1, 0, 0))
                angleValue3Input.setManipulator(adsk.core.Point3D.create(distanceValue1Input.value, distanceValue2Input.value, distanceValue3Input.value), adsk.core.Vector3D.create(1, 0, 0), adsk.core.Vector3D.create(0, 1, 0))
                            
            if cmdInput.id in ['distanceValueX','distanceValueY','distanceValueZ','angleValueRoll','angleValuePitch','angleValueYaw']:
                assert _ms.thistree.currentel.isJoint
                _ms.thistree.currentel.origin.interact(inputs) 
                #pass
            
            if cmdInput.id == 'setjoint':
                assert _ms.thistree.currentel.isJoint
                _ms.thistree.currentel.origin.jointset()
                
            if tableInput is not None:    
                _ms.oldrow = tableInput.selectedRow
        except:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


def setcurrel(tbsr,dbi, oldrow, linkselInput, jointselInput):
    global _ms
    _ms.thistree.setcurrentel(int(tbsr))
    if _ms.thistree.currentel is not None:
        row = _ms.thistree.currentel.row
        if row != oldrow:
            linkselInput.clearSelection()
            jointselInput.clearSelection()   
            #### So I also want to change the current selection so that people can see what they did:
            if 'isLink' in dir(_ms.thistree.currentel) and _ms.thistree.currentel.isLink: #link is selected
                #pass
                # linkselInput.addSelection
                for i in range(0, len(_ms.thistree.currentel.group)):
                    linkselInput.addSelection(_ms.thistree.currentel.group[i])
            elif 'isJoint' in dir(_ms.thistree.currentel) and _ms.thistree.currentel.isJoint: #joint is selected
                #pass
                # jointselInput    
                if _ms.thistree.currentel.entity:
                    jointselInput.addSelection(_ms.thistree.currentel.entity)
    else:
        row = oldrow
    alllinkstr, _ = _ms.thistree.allElements()
    #dbi.text =str(oldrow)+'\t'+str(row)+'\n'+'current element: '+ _ms.thistree.getcurrenteldesc() +  '\n' + alllinkstr
    dbi.text ='current element: '+ _ms.thistree.getcurrenteldesc() +  '\n' + alllinkstr


def getrow(commandstr,cmdid, tableInput, debugInput):
    if tableInput.selectedRow == -1:
    ### it means we have nothing selecte, so we don~t want to change anything
        pass
    else:
        elementtobedefined = tableInput.getInputAtPosition(tableInput.selectedRow,0).value    
    if commandstr in cmdid:
        _, crnum = cmdid.split(commandstr)
        #_ms.thistree.setcurrentlink(tbsr)
        #print('this when accessing table row' + crnum + str(tbsr))
        #        logging.debug('this when accessing table row' + crnum + str(tbsr))

        return crnum
    else:
        return False

# Event handler that reacts to when the command is destroyed. This terminates the script.            
class AddLinkCommandDestroyHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            global _ms
            logging.info("shutting down.")
            # When the command is done, terminate the script
            # This will release all globals which will remove all event handlers
            for handler in logging.root.handlers[:]:
                handler.close()                    
                if not runfrommenu: 
                    logging.root.removeHandler(handler)
            global _ms
            del(_ms)
            _ms = []
            if runfrommenu:
                pass
                #adsk.terminate()
        except:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


class AddLinkCommandExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            global _ms
            logging.debug('started execute! ')
            _ms = MotherShip()

            #eventArgs = adsk.core.CommandEventArgs.cast(args)    
            #inputs = eventArgs.inputs
            #cmdInput = eventArgs.input
    
            base_directory, meshes_directory, components_directory = createpaths(_ms.packagename)
            
            urdfroot = etree.Element("robot", name = "gummi")
            
            base_link = Link('base_link',-1)
            base_link.makexml(urdfroot)
            #
            setaxisjoint = Joint('set_worldaxis',-1)
            setaxisjoint.isset = True
            setaxisjoint.type = "fixed"
            setaxisjoint.realorigin.rpy = str(PI/2)+' 0 0'
            setaxisjoint.parentlink = 'base_link'
            setaxisjoint.childlink = 'base'
            setaxisjoint.makexml(urdfroot)
            
#            _ms.thistree.currentlink.genlink(meshes_directory)
#            #currentlink.name = linkInput.value
#            _ms.thistree.currentlink.makelinkxml(urdfroot)      
            allelstr, allels =  _ms.thistree.allElements()
            logging.info('found '+ str(len(allels)) + allelstr)            
            
            for i in range(0,len(allels)):
                if 'isLink' in dir(allels[i]) and allels[i].isLink:
                    allels[i].genlink(meshes_directory, components_directory)
            #currentlink.name = linkInput.value
                allels[i].makexml(urdfroot)    
            
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
    
            # Code to react to the event.
            #_ui.messageBox('In MyExecuteHandler event handler.')
        except:
            logging.error('Failed:\n{}'.format(traceback.format_exc()))
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
        
# Event handler that reacts when the command definitio is executed which
# results in the command being created and this event being fired.
class AddLinkCommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
                        
            global _ms
            _ms = MotherShip()
            # Get the command that was created.
            cmd = adsk.core.Command.cast(args.command)
            
            # Connect to the command destroyed event.
            onDestroy = AddLinkCommandDestroyHandler()
            cmd.destroy.add(onDestroy)
            _handlers.append(onDestroy)

            # Connect to the input changed event.           
            onInputChanged = AddLinkCommandInputChangedHandler()
            cmd.inputChanged.add(onInputChanged)
            _handlers.append(onInputChanged)    

            onExecute = AddLinkCommandExecuteHandler()
            cmd.execute.add(onExecute)
            _handlers.append(onExecute)

            # Get the CommandInputs collection associated with the command.
            inputs = cmd.commandInputs           
            

            # Create a tab input.
            tabCmdInput3 = inputs.addTabCommandInput('tab_1', 'Add Link')   
            tab3ChildInputs = tabCmdInput3.children
            
            tab3ChildInputs.addStringValueInput('packagename','Name of your URDF package', _ms.packagename)
            #tab3ChildInputs.addStringValueInput('packagename','Name of your URDF package', 'mypackage')
            ### TODO: needs to be set up with _ms.packagename when _ms is created!            
            
            # Create table input
            tableInput = tab3ChildInputs.addTableCommandInput('table', 'Table', 3, '1:2:3:1')
            
            tableInput.maximumVisibleRows = 20            
            tableInput.minimumVisibleRows = 10
#            addRowToTable(tableInput,'Link')
#            
#            tableInput.getInputAtPosition(_ms.rowNumber-1,1).isEnabled = False
#            logging.debug('adding link. row number'+str(_ms.rowNumber))
#            linkname = tableInput.getInputAtPosition(_ms.rowNumber-1,2).value
#            logging.debug('adding link:' + str(linkname))
#            _ms.thistree.addLink(linkname,_ms.rowNumber-1)


            # Add inputs into the table.            
            #addButtonInput = tab3ChildInputs.addBoolValueInput('tableAdd', 'Add', False, '', True)
            #tableInput.addToolbarCommandInput(addButtonInput)
            #### im removing add and create because of reasons.
            addLinkButtonInput = tab3ChildInputs.addBoolValueInput('tableLinkAdd', 'Add Link', False, '', True)
            tableInput.addToolbarCommandInput(addLinkButtonInput)
            addJointButtonInput = tab3ChildInputs.addBoolValueInput('tableJointAdd', 'Add joint', False, '', True)
            tableInput.addToolbarCommandInput(addJointButtonInput)
            
            deleteButtonInput = tab3ChildInputs.addBoolValueInput('tableDelete', 'Delete', False, '', True)
            tableInput.addToolbarCommandInput(deleteButtonInput)
            #createButtonInput = tab3ChildInputs.addBoolValueInput('tableCreate', 'Create', False, '', True)
            #tableInput.addToolbarCommandInput(createButtonInput)
            
            # Create a read only textbox input.
            #tab1ChildInputs.addTextBoxCommandInput('readonly_textBox', 'URDF TREE', 'this would be the tree', 10, True)

          
            # Create a message that spans the entire width of the dialog by leaving out the "name" argument.
            #message = '<div align="center">For more information on how to create an URDF, visit <a href="http:lmgtfy.com/?q=how+to+create+an+urdf">our website.</a></div>'
            #tab3ChildInputs.addTextBoxCommandInput('fullWidth_textBox', '', message, 1, True)            

            ##create thing that shows tree of links and joints
            tab3ChildInputs.addBoolValueInput('createtree','Create tree',  False,'', True)

            # Create a message that spans the entire width of the dialog by leaving out the "name" argument.
            messaged = ''
            tab3ChildInputs.addTextBoxCommandInput('debugbox', '', messaged, 10, True)            

            # add group for link stuff            
            mylinkgroup = tab3ChildInputs.addGroupCommandInput('linkgroup', 'Link stuff' )
            mylinkgroup.isVisible = False
            
            # Create a selection input.
            selectionInput1 = mylinkgroup.children.addSelectionInput('linkselection', 'Select Link Components', 'Basic select command input')
            selectionInput1.addSelectionFilter('Occurrences')
            selectionInput1.setSelectionLimits(0)
            
            # add group for link stuff            
            myjointgroup = tab3ChildInputs.addGroupCommandInput('jointgroup', 'Joint stuff' )
            myjointgroup.isVisible = False
            
            #global jtctrl
            jtctrl = myjointgroup.children
            allvisible = True
            allenabled = False
            
            jtctrl.addBoolValueInput('setjoint','Set Joint',  False,'', True)
            
            distanceValueInput = jtctrl.addDistanceValueCommandInput('distanceValueX', 'X', adsk.core.ValueInput.createByReal(0))#self.x+epsilon))
            distanceValueInput.setManipulator(adsk.core.Point3D.create(0, 0, 0), adsk.core.Vector3D.create(1, 0, 0))
            #return
            distanceValueInput.hasMinimumValue = False
            distanceValueInput.hasMaximumValue = False
            distanceValueInput.isVisible = allvisible
            distanceValueInput.isEnabled = allenabled
            
            # Create distance value input 2.
            distanceValueInput2 = jtctrl.addDistanceValueCommandInput('distanceValueY', 'Y', adsk.core.ValueInput.createByReal(0))#self.y+epsilon))
            distanceValueInput2.setManipulator(adsk.core.Point3D.create(0, 0, 0), adsk.core.Vector3D.create(0, 1, 0))
            distanceValueInput2.hasMinimumValue = False
            distanceValueInput2.hasMaximumValue = False
            distanceValueInput2.isVisible = allvisible
            distanceValueInput2.isEnabled = allenabled
            
            # Create distance value input 3.
            distanceValueInput3 = jtctrl.addDistanceValueCommandInput('distanceValueZ', 'Z', adsk.core.ValueInput.createByReal(0))#self.z+epsilon))
            distanceValueInput3.setManipulator(adsk.core.Point3D.create(0, 0, 0), adsk.core.Vector3D.create(0, 0, 1))
            distanceValueInput3.hasMinimumValue = False
            distanceValueInput3.hasMaximumValue = False     
            distanceValueInput3.isVisible = allvisible
            distanceValueInput3.isEnabled = allenabled
            
            # Create angle value input 1.
            angleValueInput = jtctrl.addAngleValueCommandInput('angleValueRoll', 'Roll', adsk.core.ValueInput.createByReal(0))#self.r+epsilon))
            angleValueInput.setManipulator(adsk.core.Point3D.create(0, 0, 0), adsk.core.Vector3D.create(0, 1, 0), adsk.core.Vector3D.create(0, 0, 1))
            angleValueInput.hasMinimumValue = False
            angleValueInput.hasMaximumValue = False
            angleValueInput.isVisible = allvisible
            angleValueInput.isEnabled = allenabled        
            
            # Create angle value input 2.
            angleValueInput2 = jtctrl.addAngleValueCommandInput('angleValuePitch', 'Pitch', adsk.core.ValueInput.createByReal(0))#self.p+epsilon))
            angleValueInput2.setManipulator(adsk.core.Point3D.create(0, 0, 0), adsk.core.Vector3D.create(0, 0, 1), adsk.core.Vector3D.create(1, 0, 0))
            angleValueInput2.hasMinimumValue = False
            angleValueInput2.hasMaximumValue = False
            angleValueInput2.isVisible = allvisible
            angleValueInput2.isEnabled = allenabled
            
            # Create angle value input 3.
            angleValueInput3 = jtctrl.addAngleValueCommandInput('angleValueYaw', 'Yaw', adsk.core.ValueInput.createByReal(0))#self.yaw+epsilon))
            angleValueInput3.setManipulator(adsk.core.Point3D.create(0, 0, 0), adsk.core.Vector3D.create(1, 0, 0), adsk.core.Vector3D.create(0, 1, 0))
            angleValueInput3.hasMinimumValue = False
            angleValueInput3.hasMaximumValue = False  
            angleValueInput3.isVisibile = allvisible
            angleValueInput3.isEnabled = allenabled
            
            
            # Create a selection input.
            selectionInput2 =myjointgroup.children.addSelectionInput('jointselection', 'Select Joint', 'Basic select command input')
            selectionInput2.addSelectionFilter('Joints')
            selectionInput2.setSelectionLimits(1)
            selectionInput2.isEnabled = False
            
            # Create a string value input.
            parentlinkin = myjointgroup.children.addDropDownCommandInput('parentlinkname', 'Name of parent link', 1)
                        
            childlinkin = myjointgroup.children.addDropDownCommandInput('childlinkname', 'Name of child link', 1)
            
            
            
        except:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


def createpaths(_ms_packagename):
    folderDlg = _ui.createFolderDialog()
    folderDlg.title = 'Choose location to save your URDF new package' 
    folderDlg.initialDirectory = os.path.join(os.path.expanduser("~"),'Documents')
    dlgResult = folderDlg.showDialog()
    if dlgResult != adsk.core.DialogResults.DialogOK:
        _ui.messageBox('you need to select a folder!')
        raise ValueError('Directory not selected. cannot continue.')
    outputdir = os.path.join(folderDlg.folder,_ms_packagename)
    thisscriptpath = os.path.dirname(os.path.realpath(__file__))
    base_directory = os.path.abspath(outputdir)
    _ui.messageBox(base_directory)
    if not os.path.exists(base_directory):
        os.makedirs(base_directory)
    meshes_directory = os.path.join(base_directory, "meshes/")
    _ui.messageBox( meshes_directory)
    components_directory =  os.path.join(base_directory, "components/")
    _ui.messageBox(components_directory)
    if not os.path.exists(meshes_directory):
        os.makedirs(meshes_directory)    
    if not os.path.exists(components_directory):
        os.makedirs(components_directory)    
        
    filestochange = ['display.launch', 'urdf_.rviz', 'package.xml', 'CMakeLists.txt' ] ##actually urdf.rviz is the same, but i didnt want to make another method just to copy. when i have more files i need to copy i will do it. 
    #myfilename = 'display.launch'
    for myfilename in filestochange:
        # Read in the file
        #_ui.messageBox(thisscriptpath)
        with open( os.path.join(thisscriptpath,'resources/', myfilename), 'r') as file :
          filedata = file.read()
        
        # Replace the target string
        filedata = filedata.replace('somepackage', _ms_packagename)
        
        # Write the file out again
        with open( os.path.join(base_directory, myfilename), 'w') as file:
          file.write(filedata)
    return base_directory, meshes_directory, components_directory

thisdocsunits = ''

class GenSTLCommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            global _ui, _design
            _app = adsk.core.Application.get()
            #_ui = _app.userInterface
            product = _app.activeProduct
            _design = adsk.fusion.Design.cast(product)
#            # Get the command that was created.
#            cmd = adsk.core.Command.cast(args.command)
#            
#            # Connect to the command destroyed event.
#            onDestroy = GenSTLCommandDestroyHandler()
#            cmd.destroy.add(onDestroy)
#            _handlers.append(onDestroy)
#
#            # Connect to the input changed event.           
#            onInputChanged = GenSTLCommandInputChangedHandler()
#            cmd.inputChanged.add(onInputChanged)
#            _handlers.append(onInputChanged)    
#
#            onExecute = GenSTLCommandExecuteHandler()
#            cmd.execute.add(onExecute)
#            _handlers.append(onExecute)
            


            logging.debug('starting genSTL')
            # Get the root component of the active design
            rootComp = _design.rootComponent
    
            # Create two new components under root component
            allOccs = rootComp.allOccurrences                    
            
            # create a single exportManager instance
            exportMgr = _design.exportManager
            
            
            fileDlg = _ui.createFileDialog()
            fileDlg.isMultiSelectEnabled = False
            fileDlg.title = 'Choose location to save your STL ' 
            fileDlg.filter = '*.stl'
            fileDlg.initialDirectory = os.path.join(os.path.expanduser("~"),'Documents')
            dlgResult = fileDlg.showSave()
            if dlgResult != adsk.core.DialogResults.DialogOK:
                _ui.messageBox('you need to select a folder!')
                return
            
                       # export the root component to printer utility
            stlRootOptions = exportMgr.createSTLExportOptions(rootComp,  fileDlg.filename)
    
            # get all available print utilities
            #printUtils = stlRootOptions.availablePrintUtilities
    
            # export the root component to the print utility, instead of a specified file
            #for printUtil in printUtils:
            #    stlRootOptions.sendToPrintUtility = True
            #   stlRootOptions.printUtility = printUtil
            stlRootOptions.sendToPrintUtility = False
            logging.info('saving STL file: '+ fileDlg.filename)
            exportMgr.execute(stlRootOptions)
            _ui.messageBox('file {} saved successfully'.format(fileDlg.filename))
        
        except:
            logging.error('Failed:\n{}'.format(traceback.format_exc()))
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

def run(context):
    try:
        global _app, _ui, _design, _ms, thisdocsunits
        _app = adsk.core.Application.get()
        _ui = _app.userInterface
        product = _app.activeProduct
        _design = adsk.fusion.Design.cast(product)
        
        #createpaths('batatas')
        thisdocsunits = _design.unitsManager.defaultLengthUnits         
        
        #if thisdocsunits != 'm':
        #     _ui.messageBox('So, funny thing, I have no idea on how to set default units and set them back using this API. As far as I am aware, it is currently(18-08-2018) impossible. So you need to change this documents units to meters and also make meters default for the URDF to be generated the right way - I have to create new documents, so if you don''t change the default, it won''t work\n. Once Autodesk either responds my forum question, or fixes ExportManager or allows for non-uniform affine transformations, this will no longer be necessary. ')
        #     return
        #a = adsk.core.Matrix3D.create()        
        
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        FORMAT = "[%(filename)s:%(lineno)s - %(funcName)20s() ] %(levelname)s: %(message)s"
        logging.basicConfig(filename=os.path.join(os.path.expanduser("~"),'urdfgen.log'),level=logging.DEBUG,format=FORMAT)

        workSpace = _ui.workspaces.itemById('FusionSolidEnvironment')
        tbPanels = workSpace.toolbarPanels
        
#        global tbPanel
        tbPanel = tbPanels.itemById('SolidScriptsAddinsPanel')
#        if tbPanel:
#            tbPanel.deleteMe()
#        tbPanel = tbPanels.add('NewPanel', 'New Panel', 'SolidScriptsAddinsPanel', False)


        # Get the existing command definition or create it if it doesn't already exist.
        addlinkcmdDef = _ui.commandDefinitions.itemById('cmdInputsAddLink')
        if not addlinkcmdDef:
            addlinkcmdDef = _ui.commandDefinitions.addButtonDefinition('cmdInputsAddLink', 'Make URDF', 'My attempt to make an URDF.')
        else:
            pass

        genSTLcmdDef = _ui.commandDefinitions.itemById('cmdInputsgenSTL')
        if not genSTLcmdDef:
            genSTLcmdDef = _ui.commandDefinitions.addButtonDefinition('cmdInputsgenSTL', 'Generate STL', 'Generate single STL (in case some of them are incorrect/changed)')
        else:
            pass

        # Connect to the command created event.
        onCommandCreated = AddLinkCommandCreatedHandler()
        addlinkcmdDef.commandCreated.add(onCommandCreated)
        _handlers.append(onCommandCreated)
        
        on2CommandCreated = GenSTLCommandCreatedHandler()
        genSTLcmdDef.commandCreated.add(on2CommandCreated)
        _handlers.append(on2CommandCreated)
        #_ms.thistree = UrdfTree()
        if runfrommenu:
            
            # will try to create a button for this guy
            # but first morruca
            while tbPanel.controls.itemById('cmdInputsAddLink'):
                a = tbPanel.controls.itemById('cmdInputsAddLink')
                a.deleteMe()
            
            while tbPanel.controls.itemById('cmdInputsgenSTL'):
                a = tbPanel.controls.itemById('cmdInputsgenSTL')
                a.deleteMe()
            
            tbPanel.controls.addCommand(addlinkcmdDef)          
            tbPanel.controls.addCommand(genSTLcmdDef)  
            
        else:
           # _ms = MotherShip()
            # Execute the command definition.
            addlinkcmdDef.execute()
        
        # Prevent this module from being terminated when the script returns, because we are waiting for event handlers to fire.
        #adsk.autoTerminate(False)
        
    except:
        #i need to close and destroy stuff otherwise Fusion crashes...
        try:
            logging.info("shutting down from failure or debugquit.")
            # When the command is done, terminate the script
            # This will release all globals which will remove all event handlers
            if runfrommenu: 
               for handler in logging.root.handlers[:]:
                   handler.close()
                   logging.root.removeHandler(handler)

            del(_ms)
            _ms = []
            if runfrommenu:
                pass
                #adsk.terminate()
        except:
            _ui.messageBox('Failed in shutdown sequence!:\n{}'.format(traceback.format_exc()))
        if _ui:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
            
def stop(context):
    global _ui,_app,_design,_handlers,_ms,runfrommenu
    logging.info("stopping addin")
    
    try:
        workSpace = _ui.workspaces.itemById('FusionSolidEnvironment')
        tbPanels = workSpace.toolbarPanels
        
        tbPanel = tbPanels.itemById('SolidScriptsAddinsPanel')

        #genSTLcmdDef = _ui.commandDefinitions.itemById('cmdInputsgenSTL')
        #addlinkcmdDef = _ui.commandDefinitions.itemById('cmdInputsAddLink')
        logging.info("stopping addin2")  
        if runfrommenu:
            while tbPanel.controls.itemById('cmdInputsAddLink'):
                logging.info("stopping addin3")
                a = tbPanel.controls.itemById('cmdInputsAddLink')
                a.deleteMe()
            
            while tbPanel.controls.itemById('cmdInputsgenSTL'):
                logging.info("stopping addin4")
                a = tbPanel.controls.itemById('cmdInputsgenSTL')
                a.deleteMe()
        logging.info("stopping addin5")
        _ui.messageBox('Stop addin')
        #_app = None
        #_ui  = None
        #_design = None
        
        #
        
        # Global set of event handlers to keep them referenced for the duration of the command
        _handlers = []
        _ms = []
        #del(_ui,_app,_design,_handlers,_ms,runfrommenu)
        #adsk.terminate()
        logging.info("stopping addin6")
    except:
        logging.error('Failed hard while stopping:\n{}'.format(traceback.format_exc()))
        if _ui:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))