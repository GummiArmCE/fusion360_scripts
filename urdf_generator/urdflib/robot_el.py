# -*- coding: utf-8 -*-

#Author- Frederico B. Klein
#Description- URDFGEN command - somewhat functional.
import adsk.core, adsk.fusion, traceback
import xml.etree.cElementTree as etree
#import xml.dom.minidom # for prettying it....
#import inspect
import logging
import re
#from copy import deepcopy ### pickle cant copy any swig object...

PI = 3.14159265359

       
class UrdfTree:
    def __init__(self):
        self.elementsdict = {}
        self.currentel = None
        #self.placedlinks = []

    def addLink(self, linkname,linknum,packagename):
        thislink = Link(linkname,linknum,packagename) 
        self.elementsdict.update({linknum:thislink})
        
    def addJoint(self, jointname,jointnum):
        thisjoint = Joint(jointname,jointnum) 
        self.elementsdict.update({jointnum:thisjoint})
        
    def rmElement(self,linknumstr,rowNumber): #rowNumber = _ms.rowNumber
        linknum = int(linknumstr)
        logging.debug('deleted element' + str(linknum)+ 'named: '+ self.elementsdict[linknum].name)
        self.elementsdict.pop(linknum)
        #global _ms      
        #_ms.rowNumber -=1
        return rowNumber -1 ### we need to check calls for this and make sure we read this result and update _ms!!!
        
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
                    #_ui.messageBox(report) ### or i could have used assert and did it all in one line...

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
                
        #_ui.messageBox(report+'\n')
        logging.debug( str(placedeldic)+'\n'+str(self.elementsdict))
        
        return report
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
        
#TODO: this is maybe ui stuff? the difference here is difficult for me to grasp
        
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
    def __init__(self,occname,row,packagename):
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
        self.packagename = packagename # _ms.packagename
        
    def updatepackagename(self,packagename): ### needs to be called each time packagename changes!
        self.packagename = packagename # _ms.packagename
        
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
        self.visual.geometryfilename = "package://"+self.packagename+"/meshes/" + clearupst(self.name) +".stl"

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
        

    def genlink(self,meshes_directory, components_directory, thisDesign, thisUnitsMgr, thisApp): # thisDesign = _design,  thisUnitsMgr = _unitsMgr, thisApp = _app
        didifail = 0        
        self.isVirtual = False
        try:            
            logging.debug('starting genlink')

            # Get the root component of the active design
            rootComp = thisDesign.rootComponent
            
            # Create two new components under root component
            allOccs = rootComp.allOccurrences                    
            
            # create a single exportManager instance
            exportMgr = thisDesign.exportManager
            
            ###TODO: this needs to be done for the joints as well. aff...
            removejointtranslation = adsk.core.Matrix3D.create()
            translation = adsk.core.Vector3D.create(thisUnitsMgr.convert(-self.coordinatesystem.x, thisUnitsMgr.internalUnits,'m'), thisUnitsMgr.convert(-self.coordinatesystem.y, thisUnitsMgr.internalUnits,'m'), thisUnitsMgr.convert(-self.coordinatesystem.z, thisUnitsMgr.internalUnits,'m'))
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
                            #trying to break the links here...
                            #lasttm = adsk.core.Matrix3D.create()
                            #lasttm.setWithArray(allOccs.item(l).transform.asArray())
                            
                            newrotl.append(lasttm)
                            logging.debug(allOccs.item(l).fullPathName)
                            
                            logging.debug('with tm:' + str(lasttm.asArray() ))
                            ### I am doing something wrong here. It works, sometimes, but some items are very very wrong. I wonder if it is a units problem. I am going to try to at least catch it:
                            logging.debug('translations of tm are:'+ str(lasttm.translation.asArray()))
                            
                            #newrot.transformBy(allOccs.item(l).transform)
                    ### now that i have all the occurrences names i need to get them from allOccs(?!)
                lasttransform = self.group[i].transform.copy()
                
                newrotl.append(lasttransform)
                
                newrot = removejointtranslation
                for j in range(0,len(newrotl)):

                    lasttm = newrotl[j]
 #                   largestallowedtranslation = 1 # so more than 1 meter we will go crazy.
 #                   if any([aaa>largestallowedtranslation for aaa in lasttm.translation.asArray()]):                
                    try:
                        logging.info('??:')

                        logging.debug(lasttm.translation.asArray())
                        othertm = adsk.core.Matrix3D.create()
                        

                        #lasttm.translation.scaleBy(scale)
                        #othertm.translation.setWithArray((thistranslation[0]*scale,thistranslation[1]*scale,thistranslation[2]*scale))
                        for ii in range(0,4):
                            for jj in range(0,4):
                                if (jj == 3) and (ii != 3):
                                    othertm.setCell(ii,jj,thisUnitsMgr.convert(lasttm.getCell(ii,jj), thisUnitsMgr.internalUnits,'m'))
                                else:                                                
                                    othertm.setCell(ii,jj,lasttm.getCell(ii,jj))
                        logging.info('transformed to mm:')
                        logging.debug(othertm.translation.asArray())   
                        logging.info('whole tm:')
                        logging.debug(othertm.asArray())   
                        #logging.info('transformed to cm:')
                        #logging.debug(thistmarray/100)
                        logging.info('and then we need to get it back into newrotl')
                        newrotl.pop(j)
                        newrotl.insert(j,othertm)
                    except:
                        logging.debug('could not output corrections. {}'.format(traceback.format_exc()))

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
            doc = thisApp.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
            doc.name = self.name
            
            product = thisApp.activeProduct
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
            importManager = thisApp.importManager            
            
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
            
            self.visual.geometryfilename = "package://"+self.packagename+"/meshes/" + stlname +".stl"
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
        
        report = ''
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
                logging.error('Could not set joint origin using first element!! This is quite possibly a bug in the API.\n{}\n'.format(traceback.format_exc()))

                self.origin.setxyz(joint.geometryOrOriginTwo.origin.x, joint.geometryOrOriginTwo.origin.y, joint.geometryOrOriginTwo.origin.z)
                self.origin.setxyzrpy(inputs)
            except:                        
                #_ui.messageBox('Could not set joint origin. This will affect the whole assembly and it will be hard to fix!!! This is quite possibly a bug in the API. {}'.format(traceback.format_exc()))
                report = report + 'Could not set joint origin. This will affect the whole assembly and it will be hard to fix!!! This is quite possibly a bug in the API. {}'.format(traceback.format_exc())

                logging.error('Could not set joint origin with second element either!!. This is quite possibly a bug in the API. \n{}\n'.format(traceback.format_exc()))
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
            report = report + 'could not set joint type or limits. Setting it to fixed. This is quite possibly a bug in the API. {}'.format(traceback.format_exc())
            # _ui.messageBox('could not set joint type or limits. Setting it to fixed. This is quite possibly a bug in the API. {}'.format(traceback.format_exc()))

            logging.warn('Could not set joint type for joint' + self.name+'. You need to edit the URDF and fix it manually.')
        return report

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
        
#def superprint(level,stringo):
#    #logger = logging.getLogger(__name__)
#    #logger.debug(spaces(level*5)+stringo)
#    logging.debug(spaces(level*5)+stringo)


def clearupst(stringo):
    strstr1 = re.sub('[:!@#$.()/-]', '',stringo)
    strstr2 = re.sub(' ', '_',strstr1)
    return strstr2

# Returns a string containing the especified number of spaces.
#def spaces(spaceCount):
#    result = ''
#    for i in range(0, spaceCount):
#        result += ' '
#
#    return result
