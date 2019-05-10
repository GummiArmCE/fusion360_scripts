#Author- Frederico B. Klein
#Description- URDFGEN command - somewhat functional.

import adsk.core, adsk.fusion, traceback
import xml.etree.cElementTree as etree
import xml.dom.minidom # for prettying it....
#import inspect
import logging
#import re
import os, sys
#from copy import deepcopy ### pickle cant copy any swig object...


dir_path = os.path.dirname(os.path.realpath(__file__))
print(dir_path)

if not dir_path in sys.path:
    sys.path.append(dir_path)

import importlib

import urdflib.robot_el   
importlib.reload(urdflib.robot_el) ## this hopefully loads the most current version of the import
    
_app = None
_ui  = None
_design = None

runfrommenu = True

SETDESIGNUNITSMETERBEFORE_BUILDINGTMS = True

# Global set of event handlers to keep them referenced for the duration of the command
_handlers = []
_ms = []
    
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
        if urdflib.ui.runfrommenu:
            
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
    global _ui,_app,_design,_handlers,_ms
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
            
            
            
            
            
####### my attempts to orgazine this have been thwarted by horrible code
            
            
            
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
        self.thistree = urdflib.robot_el.UrdfTree()

# probably would make more sense to make this a function of mothership?
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
                    _ms.thistree.addLink(linkname,_ms.elnum -1,_ms.packagename)
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
               texto = _ms.thistree.currentel.setjoint( jointselInput.selection(0).entity,cmdInput.id,inputs)
               if texto:
                   _ui.messageBox()
            
            if cmdInput.id == 'createtree':
                #linkselInput.hasFocus = True #### if this is not set, then you cannot click OK idk why...
                ### actually it is worse. if you don~t have a selection from the selection thing as active, it will not let you execute it.
                ### so horrible not realy a fix:                
                chcontrols(jointgroupInput.children,False,False)
                linkgroupInput.isVisible = False
                jointgroupInput.isVisible = False                
                _ui.messageBox(_ms.thistree.gentree())
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
            logging.debug('started execute! ')
            global _app, _ui, _design, _ms, _unitsMgr
            _app = adsk.core.Application.get()
            _ui = _app.userInterface
            product = _app.activeProduct
            _design = adsk.fusion.Design.cast(product)
                        ### I am updating these guys because I was having strange errors over deleted elements, which I think means I was working in the wrong design (or not updating it properly). not sure, if this does not fix it, it should be removed

            #if SETDESIGNUNITSMETERBEFORE_BUILDINGTMS:            
                ### setting units to meters so stls will have proper sizes!
            _unitsMgr = _design.fusionUnitsManager
    
            #    unitsMgr.distanceDisplayUnits = adsk.fusion.DistanceUnits.MeterDistanceUnits
        

            #_ms = MotherShip()

            #eventArgs = adsk.core.CommandEventArgs.cast(args)    
            #inputs = eventArgs.inputs
            #cmdInput = eventArgs.input
    
            base_directory, meshes_directory, components_directory = createpaths(_ms.packagename)
            
            urdfroot = etree.Element("robot", name = "gummi")
            
            base_link = urdflib.robot_el.Link('base_link',-1,_ms.packagename)
            base_link.makexml(urdfroot)
            #
            setaxisjoint = urdflib.robot_el.Joint('set_worldaxis',-1)
            setaxisjoint.isset = True
            setaxisjoint.type = "fixed"
            setaxisjoint.realorigin.rpy = str(urdflib.robot_el.PI/2)+' 0 0'
            setaxisjoint.parentlink = 'base_link'
            setaxisjoint.childlink = 'base'
            setaxisjoint.makexml(urdfroot)
            
#            _ms.thistree.currentlink.thisApp(meshes_directory)
#            #currentlink.name = linkInput.value
#            _ms.thistree.currentlink.makelinkxml(urdfroot)      
            allelstr, allels =  _ms.thistree.allElements()
            logging.info('found '+ str(len(allels)) + allelstr)            
            
            for i in range(0,len(allels)):
                if 'isLink' in dir(allels[i]) and allels[i].isLink:
                    allels[i].genlink(meshes_directory, components_directory, _design, _unitsMgr, thisApp = _app)
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
            
            