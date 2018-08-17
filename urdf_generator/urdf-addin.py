#Author-Autodesk Inc.
#Description-Demo command input examples
import adsk.core, adsk.fusion, traceback
import xml.etree.cElementTree as etree
import xml.dom.minidom # for prettying it....
import inspect
import logging
import re
import os , sys


_app = None
_ui  = None
_design = None
_rowNumber = 0
_linknum = 0
_linkname = 'link' + str(_linknum)

# Global set of event handlers to keep them referenced for the duration of the command
_handlers = []
_thistree = None

class UrdfTree:
    def __init__(self):
        self.elementsdict = {}
        self.currentel = None

    def addLink(self, linkname,linknum):
        thislink = Link(linkname,linknum) 
        self.elementsdict.update({linknum:thislink})
        
    def addJoint(self, jointname,jointnum):
        thisjoint = Joint(jointname,jointnum) 
        self.elementsdict.update({jointnum:thisjoint})
        
    def rmLink(self,linknum):
        self.elementslist.pop(linknum)
        self.elementsIDlist.pop(linknum)
        
    def allLinks(self):
        exstr = ''
        nolinks = True
        alllinks = []
        for el in self.elementsdict:
            if 'isLink' in dir(self.elementsdict[el]) and self.elementsdict[el].isLink:
                exstr = exstr +'link: ' + self.elementsdict[el].name + '\n'
                alllinks.append(self.elementsdict[el])
                nolinks = False
        if nolinks:
            exstr = 'no links!'
        return exstr,alllinks
        
    def allJoints(self):
        exstr = ''
        nojoints = True
        alljoints = []
        for el in self.elementsdict:
            if 'isJoint' in dir(self.elementsdict[el]) and self.elementsdict[el].isJoint:
                exstr = exstr +'joint: ' + self.elementsdict[el].name + '\n'
                alljoints.append(self.elementsdict[el])
                nojoints = False
        if nojoints:
            exstr = 'no joints!'
        return exstr,alljoints
        
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
    def __groupmembers(self,rigidgrouplist):
        self.group = rigidgrouplist.getgroupmemberships(self.name)
        return rigidgrouplist.getwholegroup(self.name)
        
    def getitems(self):
        items = ''
        for el in self.group:
            items = items + el.name + '\n'
        return items
        
    def makexml(self, urdfroot):
        self.visual.geometryfilename = "package://somepackage/meshes/" + clearupst(self.name) +".stl"

        link = etree.SubElement(urdfroot, "link", name= clearupst(self.name))
        
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
        

    def genlink(self, meshes_directory):
        didifail = 0        
        
        try:            
            # Get the root component of the active design
            rootComp = _design.rootComponent
    
            # Create two new components under root component
            allOccs = rootComp.allOccurrences                    
            
            # create a single exportManager instance
            exportMgr = _design.exportManager
            
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
                newrotl.append(self.group[i].transform.copy())
                newrot = adsk.core.Matrix3D.create()
                newrot.setToIdentity()
                for j in reversed(range(0,len(newrotl))):
                    newrot.transformBy(newrotl[j])
                express = 'it'+str(i)+ '=newrot'
                exec(express)
            
            
            #stlname = rootComp.name.translate(None, ':!@#$')
            #line = re.sub('[!@#$]', '', line)
            stlname = clearupst(self.name)
            
            fileName = meshes_directory+'/' + stlname
            for i in range(0,len(self.group)):
                # export the root component to printer utility
                fileName = meshes_directory+'/' + stlname+str(i)
                logging.info('saving file '+fileName )
                logging.info('from occurrence' + self.group[i].fullPathName)
                
                logging.debug('with tm:' + str(eval('it'+str(i)+'.asArray()')))
                stpOptions = exportMgr.createSTEPExportOptions(fileName, self.group[i].component)           
                exportMgr.execute(stpOptions)
                
            # Create a document.
            doc = _app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
            
            product = _app.activeProduct
            design = adsk.fusion.Design.cast(product)
            
            # Get the root component of the active design
            rootComp = design.rootComponent
            
            
    
            # Create two new components under root component
            allOccs = rootComp.occurrences   
            
            # Get import manager
            importManager = _app.importManager            
            
            #### add occurrances from other stuff to this new stuff
            for i in range(0,len(self.group)):
                fileName = meshes_directory+'/' + stlname+str(i)+'.stp'
                logging.info('loading file: '+fileName)
                stpOptions = importManager.createSTEPImportOptions(fileName)
                importManager.importToTarget(stpOptions, rootComp)
            for i in range(0,len(rootComp.occurrences)):
                rootComp.occurrences.item(i).transform = eval('it'+str(i))
                pass
            
            ###TODO:
            ### must set mass and center of inertia! i think visual and origins are correct because this info is in the stl...
            logging.info('XYZ moments of inertia:'+str(rootComp.physicalProperties.getXYZMomentsOfInertia()))
            logging.info('Mass:'+str(rootComp.physicalProperties.mass))
            
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
    
            exportMgr.execute(stlRootOptions)            
            
            self.visual.geometryfilename = "package://somepackage/meshes/" + stlname +".stl"
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
        self.origin = OrVec()
        self.parentlink = ''
        self.childlink = ''
        self.axis = '0 0 0'
        self.limit = Limit()
        self.level = level
        self.type = ''
        self.row = row # i am not sure why i am savign this...
        self.isJoint = True
    def setjoint(self,joint):#,parentl,childl):
        #self.parentlink = parentl
        #self.childlink = childl
        
        #python doesnt have a switch statement, i repeat python does not have a switch statement...
        #from the docs, we should implement this:
        #Name     Value     Description
        #BallJointType     6     Specifies a ball type of joint.
        #CylindricalJointType     3     Specifies a cylindrical type of joint.
        #PinSlotJointType     4     Specifies a pin-slot type of joint.
        #PlanarJointType     5     Specifies a planar type of joint.
        #RevoluteJointType     1     Specifies a revolute type of joint.
        #RigidJointType     0     Specifies a rigid type of joint.
        #SliderJointType     2     Specifies a slider type of joint.
        if joint.jointMotion.jointType is 1:
            self.type = "revolute"
            self.axis = str(joint.jointMotion.rotationAxisVector.x)+ ' ' + str(joint.jointMotion.rotationAxisVector.y)+ ' ' + str(joint.jointMotion.rotationAxisVector.z)
        if joint.jointMotion.jointType is 0:
            self.type = "fixed"
        
        haslimits = False
        if 'rotationLimits' in dir(joint.jointMotion):
            if joint.jointMotion.rotationLimits.isMinimumValueEnabled:
                self.limit.lower = joint.jointMotion.rotationLimits.minimumValue
                haslimits = True
            if joint.jointMotion.rotationLimits.isMaximumValueEnabled:
                self.limit.upper = joint.jointMotion.rotationLimits.maximumValue
                haslimits = True
        if self.type == "revolute" and not haslimits:
            self.type = "wheel"
            
    def getitems(self):
        items = 'parent:' + self.parentlink + '\n' + 'child:' + self.childlink        
        return items

    def makexml(self, urdfroot):

        joint = etree.SubElement(urdfroot, "joint", name= clearupst(self.name), type = self.type)
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
def addRowToTable(tableInput):
    # Get the CommandInputs object associated with the parent command.
    cmdInputs = adsk.core.CommandInputs.cast(tableInput.commandInputs)
    
    # Create three new command inputs.
    #valueInput = cmdInputs.addTextBoxCommandInput('TableInput_value{}'.format(_rowNumber), 'JorL', 'Link',1,True)
    JorLInput = cmdInputs.addDropDownCommandInput('TableInput_value{}'.format(_rowNumber), 'JorLTable{}'.format(_rowNumber), adsk.core.DropDownStyles.TextListDropDownStyle)
    dropdownItems = JorLInput.listItems
    dropdownItems.add('Link', True, '')
    dropdownItems.add('Joint', False,'')   
    stringInput =  cmdInputs.addStringValueInput('TableInput_string{}'.format(_rowNumber), 'StringTable{}'.format(_rowNumber), 'link' + str(_rowNumber))
    elnnumInput =  cmdInputs.addStringValueInput('elnum{}'.format(_rowNumber), 'elnumTable{}'.format(_rowNumber), str(_rowNumber))
    #spinnerInput = cmdInputs.addIntegerSpinnerCommandInput('spinnerInt{}'.format(_rowNumber), 'Integer Spinner', 0 , 100 , 2, int(_rowNumber))
    slbutInput = cmdInputs.addBoolValueInput('butselectClick{}'.format(_rowNumber),'Select',  False,'', True)
 
    
    
    elnnumInput.isEnabled = False
    # Add the inputs to the table.
    row = tableInput.rowCount
    tableInput.addCommandInput( elnnumInput, row, 0)
    tableInput.addCommandInput(JorLInput, row, 1)
    #tableInput.addCommandInput(valueInput, row, 0)
    tableInput.addCommandInput(stringInput, row, 2)
    #tableInput.addCommandInput(spinnerInput, row, 2)
    tableInput.addCommandInput(slbutInput, row, 3)
    
    # Increment a counter used to make each row unique.
    global _rowNumber, _thistree
    _rowNumber = _rowNumber + 1
    
    

# Event handler that reacts to any changes the user makes to any of the command inputs.
class AddLinkCommandInputChangedHandler(adsk.core.InputChangedEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            global _thistree, currentel        
            
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
            
            if _thistree.currentel is not None:
                oldrow = _thistree.currentel.row
            else:
                oldrow = -1
                
            
            
################################################################
            # set current link
            ### if working in main context:
            if tableInput is not None:
                setcurrel(tableInput.selectedRow,debugInput)
                
                if _thistree.currentel is not None and  _thistree.currentel.row != oldrow:
                    linkselInput.clearSelection()
                
                
                crnum = getrow('TableInput_value', cmdInput.id, tableInput.selectedRow,debugInput)
                if crnum and tableInput.selectedRow != -1 and tableInput.getInputAtPosition(tableInput.selectedRow,1).selectedItem.name == 'Joint':
                    tableInput.getInputAtPosition(tableInput.selectedRow,2).value = 'joint'+crnum
    
                    #JorLTableInput
                    ### if it is different from what it was before, then i should change the name, right?
                    #_ui.messageBox('changedstuff! in row' + rowrow)
                crnum = getrow('butselectClick', cmdInput.id, tableInput.selectedRow,debugInput)
                if crnum:
                    linkselInput.clearSelection()
                if cmdInput.id == 'tableCreate' and  tableInput.getInputAtPosition(tableInput.selectedRow,1).isEnabled:           
    
                    tableInput.getInputAtPosition(tableInput.selectedRow,1).isEnabled = False
                    ### and create stuff!!!
                    if tableInput.getInputAtPosition(tableInput.selectedRow,1).selectedItem.name == 'Link':
                        linkname = tableInput.getInputAtPosition(tableInput.selectedRow,2).value
                        logging.debug('adding link:' + str(linkname))
                        _thistree.addLink(linkname,tableInput.selectedRow)
                        setcurrel(tableInput.selectedRow,debugInput)
                    elif tableInput.getInputAtPosition(tableInput.selectedRow,1).selectedItem.name == 'Joint':
                        jointname = tableInput.getInputAtPosition(tableInput.selectedRow,2).value
                        logging.debug('adding joint:' + str(jointname))
                        _thistree.addJoint(jointname,tableInput.selectedRow)
                        setcurrel(tableInput.selectedRow,debugInput)
                        
                crnum = getrow('TableInput_string', cmdInput.id, tableInput.selectedRow,debugInput)
                if crnum:  
                    pass
                
                if cmdInput.id == 'tableAdd':
                    addRowToTable(tableInput)
                elif cmdInput.id == 'tableDelete':
                    if tableInput.selectedRow == -1:
                        _ui.messageBox('Select one row to delete.')
                    else:
    
                        _thistree.elementsdict.pop(tableInput.selectedRow)
                        tableInput.deleteRow(tableInput.selectedRow)
                        
                ### setting up visibility of joint and link group selection stufffs:
                if tableInput.selectedRow!= -1 and not tableInput.getInputAtPosition(tableInput.selectedRow,1).isEnabled and  tableInput.getInputAtPosition(tableInput.selectedRow,1).selectedItem.name == 'Link':
                    
                    linkgroupInput.isVisible = True
                    jointgroupInput.isVisible = False
                if tableInput.selectedRow!= -1 and not tableInput.getInputAtPosition(tableInput.selectedRow,1).isEnabled and  tableInput.getInputAtPosition(tableInput.selectedRow,1).selectedItem.name == 'Joint':
                    
                    linkgroupInput.isVisible = False
                    jointgroupInput.isVisible = True
                    pln = jointgroupInput.children.itemById('parentlinkname')
                    cln = jointgroupInput.children.itemById('childlinkname')
                    alllinkstr, _ = _thistree.allLinks()
                    alllinkgr = alllinkstr.split('\n')
                    for link in  alllinkgr:
                        pln.listItems.add(link, False,'')
                        cln.listItems.add(link, False,'')
                        
            if cmdInput.id == 'linkselection':
                #### wait, i think i can export a selection! so...
                #### so, if I try to select things without having set anything, it jumps here into linkselection. I don't want this to happen, so i will make it create a ballon to warn it
                if 'group' not in dir(_thistree.currentel):
                    _ui.messageBox('Must create link or joint before selecting!')
                    return
                _thistree.currentel.group = [] #### i refer to element, but i know it is a link!
                for i in range(0, linkselInput.selectionCount):
                    if linkselInput.selection(i).entity not in _thistree.currentel.group:
                        _thistree.currentel.group.append( linkselInput.selection(i).entity)
                        ##TODO:
                        # REMOVE child occurrences that can be in the list, or they will be doubled in generating the link -> larger mesh, wrong weight and moments of inertia
                        #logging.debug(dir(linkselInput.selection(i).entity))
            if cmdInput.id == 'parentlinkname':
                pln = inputs.itemById('parentlinkname')
                aa= pln.selectedItem.name.split('link: ')
                _thistree.currentel.parentlink = aa[1]
                
            if cmdInput.id == 'childlinkname':
                cln = inputs.itemById('childlinkname')
                aa= cln.selectedItem.name.split('link: ')
                _thistree.currentel.childlink = aa[1]

            if cmdInput.id == 'jointselection':
               _thistree.currentel.setjoint( jointselInput.selection(0).entity)
                        ##TODO:
                        # REMOVE child occurrences that can be in the list, or they will be doubled in generating the link -> larger mesh, wrong weight and moments of inertia
                        #logging.debug(dir(linkselInput.selection(i).entity))
            
        except:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


def setcurrel(tbsr,dbi):
    global _thistree
    _thistree.setcurrentel(tbsr)
    alllinkstr, _ = _thistree.allLinks()
    dbi.text ='current element: '+ _thistree.getcurrenteldesc() + '\n' +  '\n' + alllinkstr

def getrow(commandstr,cmdid, tbsr, debugInput):
    if commandstr in cmdid:
        _, crnum = cmdid.split(commandstr)
        #_thistree.setcurrentlink(tbsr)
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
            # When the command is done, terminate the script
            # This will release all globals which will remove all event handlers
            for handler in logging.root.handlers[:]:
                handler.close()
                logging.root.removeHandler(handler)
            
            adsk.terminate()
        except:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


class AddLinkCommandExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            global _thistree
            #eventArgs = adsk.core.CommandEventArgs.cast(args)    
            #inputs = eventArgs.inputs
            #cmdInput = eventArgs.input
    
            
            urdfroot = etree.Element("robot", name = "gummi")
            
#            _thistree.currentlink.genlink(meshes_directory)
#            #currentlink.name = linkInput.value
#            _thistree.currentlink.makelinkxml(urdfroot)      
            _, allels =  _thistree.allElements()
            for i in range(0,len(allels)):
                if 'isLink' in dir(allels[i]) and allels[i].isLink:
                    allels[i].genlink(meshes_directory)
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
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
        
# Event handler that reacts when the command definitio is executed which
# results in the command being created and this event being fired.
class AddLinkCommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
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
            
            # Create table input
            tableInput = tab3ChildInputs.addTableCommandInput('table', 'Table', 3, '1:2:3:1')
            addRowToTable(tableInput)

            # Add inputs into the table.            
            addButtonInput = tab3ChildInputs.addBoolValueInput('tableAdd', 'Add', False, '', True)
            tableInput.addToolbarCommandInput(addButtonInput)
            deleteButtonInput = tab3ChildInputs.addBoolValueInput('tableDelete', 'Delete', False, '', True)
            tableInput.addToolbarCommandInput(deleteButtonInput)
            createButtonInput = tab3ChildInputs.addBoolValueInput('tableCreate', 'Create', False, '', True)
            tableInput.addToolbarCommandInput(createButtonInput)
            
            # Create a read only textbox input.
            #tab1ChildInputs.addTextBoxCommandInput('readonly_textBox', 'URDF TREE', 'this would be the tree', 10, True)

          
            # Create a message that spans the entire width of the dialog by leaving out the "name" argument.
            message = '<div align="center">For more information on how to create an URDF, visit <a href="http:lmgtfy.com/?q=how+to+create+an+urdf">our website.</a></div>'
            tab3ChildInputs.addTextBoxCommandInput('fullWidth_textBox', '', message, 1, True)            

            # Create a message that spans the entire width of the dialog by leaving out the "name" argument.
            messaged = 'debugbox stuff'
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



base_directory = "c:/test_gummi_urdf2"
if not os.path.exists(base_directory):
    os.makedirs(base_directory)
meshes_directory = base_directory + "/meshes"
if not os.path.exists(meshes_directory):
    os.makedirs(meshes_directory)    


def run(context):
    try:
        global _app, _ui, _design, _thistree
        _app = adsk.core.Application.get()
        _ui = _app.userInterface
        product = _app.activeProduct
        _design = adsk.fusion.Design.cast(product)
        
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        logging.basicConfig(filename=os.path.join(base_directory,'urdfgen.log'),level=logging.DEBUG)

        # Get the existing command definition or create it if it doesn't already exist.
        addlinkcmdDef = _ui.commandDefinitions.itemById('cmdInputsAddLink')
        if not addlinkcmdDef:
            addlinkcmdDef = _ui.commandDefinitions.addButtonDefinition('cmdInputsAddLink', 'Make URDF', 'My attempt to make an URDF.')

        # Connect to the command created event.
        onCommandCreated = AddLinkCommandCreatedHandler()
        addlinkcmdDef.commandCreated.add(onCommandCreated)
        _handlers.append(onCommandCreated)
        
        _thistree = UrdfTree()
               
        # Execute the command definition.
        addlinkcmdDef.execute()
        
        # Prevent this module from being terminated when the script returns, because we are waiting for event handlers to fire.
        adsk.autoTerminate(False)
        
    except:
        if _ui:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))