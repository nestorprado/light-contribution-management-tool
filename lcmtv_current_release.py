import maya.cmds as cmds
import re
import maya.mel as mel
import os

class LCMT:
	"""Light Contribution Management Tool
	Version: 3.6.4
	Author: Nestor Prado
	more@nestorprado.com
	2012"""
	
	version = '[LCMT v. 3.6.4]'
	lightDB = ''
	path = ''
	fullPath = ''
	saveImages = False
	MentalRayLightTypes = ['mentalrayIblShape'] 
	RenderManLightTypes = []#['RmanEnvLightShape'] #revise with renderman
	VrayLightTypes = ['VRayLightIESShape', 'VRayLightMesh', 'VRayLightMeshLightLinking', 'VRayLightMtl', 'VRayLightRectShape', 'VRayLightSphereShape','VRayLightDomeShape']
	ArnoldLightTypes = ['aiAreaLight','aiSkyDomeLight']
	
	#Bug fix Issue #1 and #8 
	NonGeoTypes = ['cylindricalLightLocator', 'discLightLocator', 'rectangularLightLocator', 'sphericalLightLocator']

	lightTypes = []

	def __init__(self):
		#Create new file for database if there isn't one
		self.path = cmds.workspace(q=True, rd=True)+'scripts/'
		self.fullPath = self.path + 'LCMT_lightTypesDB.txt'
		self.saveImages = False
		#if file doesn't exist
		if not os.path.exists(self.fullPath):
			#check to see if there is a scripts directory in the project space
			if not os.path.exists(self.path):
				os.makedirs(self.path)
			f = open(self.fullPath, 'w')
			f.write('key|bounce|rim|background|wall|kick')
			f.close()
			self.lightDB = 'key|bounce|rim|background|wall|kick'
		else:
			#if the file exists initialize write the lightDB parameter
			f = open(self.fullPath, 'r')
			content = f.read()
			self.lightDB = content
			f.close()
		#check which rendering engines are currently installed to not have any
		#errors when searching for light types in the future
		#since I don't know a quick way of querying what render engines are currently installed I'll use this workarround

		self.lightTypes.append('light') #default maya light types


		#query if mental ray is installed
		if self.isRenderEngineInstalled('mentalRay'):
			self.lightTypes += self.MentalRayLightTypes
			print self.version, "Mental Ray is installed"

		#query if RenderMan is installed
		if self.isRenderEngineInstalled('renderman'):
			self.lightTypes += self.RenderManLightTypes
			print self.version, "Renderman is installed"
			
		#query if Vray is installed
		if self.isRenderEngineInstalled('vray'):
			self.lightTypes += self.VrayLightTypes
			self.NonGeoTypes.append('VRayEnvironmentPreview')
			print self.version, "Vray is installed"


		#query if Arnold is Installed
		if self.isRenderEngineInstalled('arnold'):
			self.lightTypes += self.ArnoldLightTypes
			for types in self.ArnoldLightTypes:
				self.NonGeoTypes.append(types)
			print self.version, "Arnold is installed"		

		print self.version, 'current light types:', self.lightTypes	        
		print self.version, 'current NonGeoTypes', self.NonGeoTypes	        

	def isRenderEngineInstalled(self,renderEngineName):
        
        #bug fix: 06-20-2012: if mentalRay plugin not installed maya still has nodes called mentalraytexture
		#this prevents LCMT from not not working when the mentalray pluguin isn't installed by default
		if renderEngineName == 'mentalray' or renderEngineName == 'mentalRay':
			renderEngineName =  self.MentalRayLightTypes[-1]
		#Arnold compatibility
		elif renderEngineName == 'arnold':
			#Since all there is no node specifically named arnold we use the 
			#standard shader node name to see if arnold is indeed installed or no
			renderEngineName = 'aiStandard'
			
		#query all the types and look for Vray Types, and Renderman Types
		AllTypes = cmds.allNodeTypes()
		regex = '\w*'+renderEngineName+'\w*'    
		to_find = re.compile(regex,re.IGNORECASE)
		to_search = ", ".join(AllTypes)
		match = re.search(to_find, to_search)

		if match!=None:
			#print 'Found',renderEngineName
			#print match.group()
			return True
		else:
			print self.version, 'Didn\'t find',renderEngineName
			return False
   
	def addLightTypesToFile(self, newContents=''):

		if os.path.exists(self.fullPath):
			f = open(self.fullPath, 'a')
			f.write('|'+newContents)
			f.close()
			f = open(self.fullPath, 'r')
			self.lightDB = f.read()
			f.close()

		else:
			print 'ERROR Writing file: ', self.fullPath, 'it doesn\'t EXIST!!'
			return -1


	def extractLightName(self, name):
		lightTypes = self.lightDB
		to_find = re.compile(lightTypes,re.IGNORECASE)
		to_search = name
		match = re.search(to_find, to_search)
		if match!=None:
			return match.group().lower()
		else:        return name

	def groupLightsByName(self, lights):

		lightGroups = dict()
		for light in lights:
			lightNameType = self.extractLightName(light)
			if lightNameType not in lightGroups.keys():
				lightGroups[lightNameType] = [light]
			else:
				lightGroups[lightNameType].append(light)

		return lightGroups



	def createLayersFromLights(self, selectedGeometry=[], lightsSelected=[]):
		#select all the lights in the scene includin IBL nodes    
		lights = cmds.ls(type=self.lightTypes)
			
		if selectedGeometry !=None and selectedGeometry !=[]:  
			geometry = list(set(selectedGeometry) - set(lights) -set(cmds.ls(type =self.NonGeoTypes)))
		else: 
			
			#UPDATE:
			geometry =  cmds.ls(dag=True,geometry=True, selection=True)
			#Bug Fix Issue #10 (This takes out the lights that are geo types and makes sure we only have what we understand as geo
			geometry = list(set(geometry) - set(lights) -set(cmds.ls(type =self.NonGeoTypes)))
			if geometry == []:
				
		
				#select all the geometry in the scene
				geometry =  cmds.ls(geometry=True)
			#take out the ibl shapes from the geo selection
			#											   Bug fix Issue #1 and #8 
			geometry = list(set(geometry) - set(lights) -set(cmds.ls(type =self.NonGeoTypes)))   

		if lightsSelected !=None and lightsSelected !=[]:
			selectedLights = lightsSelected
		else:
			#see if there is any number of lights the the artist has selected 
			selectedLights = cmds.ls(dag=True, selection=True, type=self.lightTypes)

		#if there isn't any lights selected just create one layer for each light      
		if selectedLights == []:
			lightGroups = self.groupLightsByName(lights)
			for group in lightGroups:   
				test = lightGroups[group]
				lightTrans = cmds.listRelatives(test, p=1)   
				layerElements = geometry + lightGroups[group]
				layerName = self.extractLightName(lightGroups[group][-1])
				layerName += '_Light'
				cmds.createRenderLayer(layerElements, name=layerName)
		else:
			#if we have a certain number of lights selected create a layer with all of those lights attached
			lightTrans = cmds.listRelatives(selectedLights, p=1)   
			layerElements = geometry + lightTrans
			
			layerName = self.extractLightName(lightTrans[-1])
			cmds.createRenderLayer(layerElements, name=layerName)

	def createRenderElementsFromLights(self, selectedGeometry=[], lightsSelected=[]):
		#select all the lights in the scene includin IBL nodes    
		lights = cmds.ls(type=self.lightTypes)

		if selectedGeometry !=None and selectedGeometry !=[]:   
			geometry = selectedGeometry
		else: 

			#UPDATE:
			geometry =  cmds.ls(dag=True,geometry=True, selection=True)
			if geometry == []:
				#select all the geometry in the scene
				geometry =  cmds.ls(geometry=True)
			#take out the ibl shapes from the geo selection
			geometry = list(set(geometry) - set(lights))   

		if lightsSelected !=None and lightsSelected !=[]:
			selectedLights = lightsSelected
		else:
			#see if there is any number of lights the the artist has selected 
			selectedLights = cmds.ls(dag=True, selection=True, type=self.lightTypes)

		#if there isn't any lights selected just create one layer for each light      
		if selectedLights == []:
			lightGroups = self.groupLightsByName(lights)
			for group in lightGroups:   
				layerElements = lightGroups[group]
				layerName = self.extractLightName(lightGroups[group][-1])

				#instead of creating a render layer we create a render element light select in vray
				#cmds.createRenderLayer(layerElements, name=layerName)

				#create Render Element easier in mel
				mel.eval("vrayAddRenderElement LightSelectElement") 
				LightSelectNode = cmds.ls(selection=True)
				#rename it to something convenient
				LightSelectNode = cmds.rename(LightSelectNode, 'vrayRE_'+layerName)
				cmds.setAttr('%s.vray_name_lightselect' % LightSelectNode, layerName, type="string")
				#assign the lights to the render element that is a set in maya
				cmds.sets(layerElements, e=True, forceElement=LightSelectNode)


		else:
			#if we have a certain number of lights selected create a layer with all of those lights attached
			lightTrans = cmds.listRelatives(selectedLights, p=1)   
			layerElements = lightTrans
			layerName = self.extractLightName(lightTrans[-1])

			#instead of creating a render layer we create a render element light select in vray
			#cmds.createRenderLayer(layerElements, name=layerName)

			#create Render Element easier in mel
			mel.eval("vrayAddRenderElement LightSelectElement") 
			LightSelectNode = cmds.ls(selection=True)
			#rename it to something convenient
			LightSelectNode = cmds.rename(LightSelectNode, 'vrayRE_'+layerName)
			cmds.setAttr('%s.vray_name_lightselect' % LightSelectNode, layerName, type="string")
			#assign the lights to the render element that is a set in maya
			cmds.sets(layerElements, e=True, forceElement=LightSelectNode)

	def sortLightsByType(self, lights):
		lightTypes = []
		type=1
		for light in lights:
			type=1
			if cmds.objectType( light, isType='mentalrayIblShape' ) == True:
				type = 2
			lightTypes.append((light,type))


		lightTypes = sorted(lightTypes, key=lambda light: light[-1])
		lights = []
		for light in lightTypes:
			lights.append(light[0])
		return lights

	def saveCurrentImageInRenderView(self, filename):    
		path = cmds.file(query=True,sceneName=True)
		sceneName = os.path.split(path)[1].rsplit('.')[0]
		projectSpace = cmds.workspace(q=True, rd=True)
		imagesFolder = projectSpace + 'images/tmp/'
		editor = 'renderView'
		print 'Saving file', imagesFolder+sceneName+'_'+filename 
		cmds.renderWindowEditor(editor, e=True, writeImage=imagesFolder+sceneName+'_'+filename)

	def isLightHidden(self, light):
		lightTrans = cmds.listRelatives(light, p=1)[0]   
		return cmds.getAttr('%s.visibility' % lightTrans) == False or cmds.getAttr('%s.visibility' % light) == False

	def renderOnlyThisLight(self, lights):

		if type(lights)!=list:
			lights = [lights]
		lightNames =''
		for light in lights:
			lightNames += '_'+cmds.listRelatives(light, p=1)[0]
			wasHidden = False
			if self.isLightHidden(light) :
				cmds.showHidden(light)
				wasHidden = True

			#-Revise!--if it is an ibl light then turn off emit Final Gather
			if cmds.objectType( light, isType='mentalrayIblShape' ) == True:
				if cmds.getAttr('%s.visibleInFinalGather' % light) == False:
					cmds.setAttr('%s.visibleInFinalGather' % light, 1)

					wasHidden = True

		mel.eval("renderIntoNewWindow render")   

		#See if we are rendering with vray frame buffer and save it to the maya render buffer
		if cmds.getAttr('defaultRenderGlobals.currentRenderer') == 'vray':
			if self.isRenderEngineInstalled('vray'):
				if cmds.getAttr ("vraySettings.vfbOn"):
					mel.eval("vrend -cloneVFB")                                              

		rv = cmds.getPanel(scriptType='renderWindowPanel')
		caption = cmds.renderWindowEditor(rv, query=True, pca=True)            
		newCaption = caption+' contriburion of '+lightNames.replace('_',' ')
		cmds.renderWindowEditor(rv, edit=True, pca= newCaption)

		# save the frame in mel
		mel.eval("renderWindowMenuCommand keepImageInRenderView renderView;")

		if self.saveImages:
			self.saveCurrentImageInRenderView('contributionOf'+lightNames)

		for light in lights:
			if wasHidden:
				cmds.hide(light)
				#-Revise!-- if it was the ibl node disable final gather again
				if cmds.objectType( light, isType='mentalrayIblShape' ) == True:
					cmds.setAttr('%s.visibleInFinalGather' % light, 0)


	def renderAllLights(self, renderLights=[],useGroups=False):  
		lights = cmds.ls(dag=True,visible=True, type=self.lightTypes)  
		#Check if there is any lights selected to only do those
		if renderLights == [] or renderLights == None:
			renderLights = cmds.ls( dag=True,  sl=True , type=self.lightTypes)
		#if there isn't any light selected just get all the lights
		if renderLights == []:
			renderLights = lights

		lightNames = ""
		for light in renderLights:
			lightNames = lightNames + light + '\n' 


		windowName = 'ProgressWindow'
		if cmds.window(windowName, exists=True):
			cmds.deleteUI(windowName)

		window = cmds.window(windowName,t="Progress Report")

		cmds.columnLayout()
		cmds.iconTextStaticLabel( st='textOnly', l='Rendering Lights:' )
		cmds.iconTextStaticLabel( st='textOnly', l=lightNames )
		cmds.iconTextStaticLabel( st='textOnly', l='Process Bar' )
		progressControl = cmds.progressBar(maxValue=len(renderLights), width=300)
		cmds.showWindow( window )    

		lights = self.sortLightsByType(lights)
		#-Revised--hide ibl node that is at the end of lights list (sorted previously)
		if cmds.objectType( lights[-1], isType='mentalrayIblShape' ) == True:
			cmds.setAttr('%s.visibleInFinalGather' % lights[-1], 0)
			cmds.setAttr('%s.visibleInEnvironment' % lights[-1], 0)

		cmds.hide(lights)
		lightCount = 0

		if useGroups==True:
			renderLightsGroups = self.groupLightsByName(renderLights)
			cmds.progressBar(progressControl,edit=True, maxValue=len(renderLightsGroups.keys()), width=300)
			for group in renderLightsGroups:
				self.renderOnlyThisLight(renderLightsGroups[group]) 
				progressInc = cmds.progressBar(progressControl, edit=True, pr=lightCount+1) 
				lightCount+=1
		else:
			print renderLights
			for light in renderLights:
				self.renderOnlyThisLight(light) 
				progressInc = cmds.progressBar(progressControl, edit=True, pr=lightCount+1) 
				lightCount+=1

		cmds.showHidden(lights)  
		#-Revised--since we sorted the lights by type we know that the lastone will be the IBL
		if cmds.objectType( lights[-1], isType='mentalrayIblShape' ) == True:
			cmds.setAttr('%s.visibleInFinalGather' % lights[-1], 1)
			cmds.setAttr('%s.visibleInEnvironment' % lights[-1], 1)

	def updateScollList(self, mode, listName):

		lights = cmds.ls(dag =True,visible=True,type=self.lightTypes)  
		lightGroups = self.groupLightsByName(lights)
		if mode:
		   cmds.iconTextScrollList(listName,edit=True, ra=True)
		   cmds.iconTextScrollList(listName,edit=True, allowMultiSelection=True, append=lightGroups.keys())
		else:
		   cmds.iconTextScrollList(listName,edit=True, ra=True)
		   cmds.iconTextScrollList(listName,edit=True, allowMultiSelection=True, append=lights)

		

	def getElementsFromLightScrollList(self, listName, useGroups):
		lights = cmds.ls(dag =True,visible=True,type=self.lightTypes)  
		lightGroups = self.groupLightsByName(lights)
		selectedGroups = cmds.iconTextScrollList(listName, query=True, si=True )  
		if selectedGroups == None:
			return None  
		if cmds.checkBox(useGroups, query=True, value=True):
			returnLights = []
			for group in selectedGroups:
				returnLights.extend(lightGroups[group])
			return returnLights
		else:
			return selectedGroups

	def addLightTypes(self):
		result = cmds.promptDialog(
					title='New Light Types',
					message='Add New Light Types (Separated by comas):',
					button=['OK', 'Cancel'],
					defaultButton='OK',
					cancelButton='Cancel',
					dismissString='Cancel')

		if result == 'OK':
			text = cmds.promptDialog(query=True, text=True)
			text = text.replace(',','|')
			self.addLightTypesToFile(text)

	def displayLightTypes(self):
		 oldLightTypes = self.lightDB.replace('|',',')
		 cmds.confirmDialog(message='The Light Types in the DB are:\n'+oldLightTypes)

	def resetLightTypesToDefault(self):

		result = cmds.confirmDialog( title='Confirm', message='Are you sure?', button=['Yes','No'], defaultButton='Yes', cancelButton='No', dismissString='No' )
		if result == 'Yes':
			f = open(self.fullPath, 'w')
			f.write('key|bounce|rim|background|wall|kick')
			f.close()
			self.lightDB='key|bounce|rim|background|wall|kick'

	def toggleSaveImages(self):

		self.saveImages = not(self.saveImages)

	def isLightVray(self, light):
		#Fixes Bug 9 fixed
		for type in self.VrayLightTypes:
			if cmds.objectType( light, isAType=type ) == True:
				return True
		return False


	def changeLightParams(self,lightList,useGroupLights ,parameter):

		print "Parameter to Change", parameter
		lightsSelected = self.getElementsFromLightScrollList(lightList,useGroupLights)

		if lightsSelected !=None and lightsSelected !=[]:
			selectedLights = lightsSelected
		else:
			#see if there is any number of lights the the artist has selected 
			selectedLights = cmds.ls(dag=True, selection=True, type=self.lightTypes)

		#if there isn't any lights selected just create one layer for each light      
		if selectedLights == []:
			print "Please Select some lights"
			return

		result = cmds.promptDialog(
					title='Enter '+parameter+' value to change',
					message='Enter '+parameter+' value to change:',
					button=['OK', 'Cancel'],
					defaultButton='OK',
					cancelButton='Cancel',
					dismissString='Cancel')

		if result == 'OK':
			text = cmds.promptDialog(query=True, text=True)
		elif result == 'Cancel':
			return

		for light in selectedLights:
			if parameter == "intensity":
				#Bug 9 fixed
				if self.isLightVray(light) == True:
					cmds.setAttr('%s.intensityMult' % light, float(text))
				else:	
					cmds.setAttr('%s.intensity' % light, float(text))
			if parameter == "rename":
				#
				light = cmds.listRelatives(light, p=1) 
				cmds.rename(light, text, ignoreShape = False)
				self.refreshList(lightList)



	def refreshList(self,list):
			self.updateScollList(True, list)
			self.updateScollList(False, list)

	def createLight(self, type, lightList):

		if type == "area":
			light = cmds.shadingNode ('areaLight', asLight=True)
			cmds.setAttr('%s.useRayTraceShadows' % light, 1)
			self.refreshList(lightList)
			return
		if type == "areaMR":
			light = cmds.shadingNode ('areaLight', asLight=True)
			cmds.setAttr('%s.intensity' % light, 100)
			cmds.setAttr('%s.decayRate' % light, 2)
			cmds.setAttr('%s.useRayTraceShadows' % light, 1)
			cmds.setAttr('%s.areaLight' % light, 1)
			cmds.setAttr('%s.rayDepthLimit' % light, 2)
			
			self.refreshList(lightList)
			return
		if type == "spot":
			light = cmds.shadingNode ('spotLight', asLight=True)
			cmds.setAttr('%s.useRayTraceShadows' % light, 1)
			self.refreshList(lightList)
			return
		if type == "spotMR":
			light = cmds.shadingNode ('spotLight', asLight=True)
			cmds.setAttr('%s.intensity' % light, 100)
			cmds.setAttr('%s.decayRate' % light, 2)
			cmds.setAttr('%s.useRayTraceShadows' % light, 1)
			cmds.setAttr('%s.areaLight' % light, 1)
			cmds.setAttr('%s.areaType' % light, 1)
			cmds.setAttr('%s.rayDepthLimit' % light, 2)
			
			self.refreshList(lightList)
			return
		if type == "vrayRect":
			light = cmds.shadingNode ('VRayLightRectShape', asLight=True)
			self.refreshList(lightList)
			return
		
		if type == "vrayDome":
			light = cmds.shadingNode ('VRayLightDomeShape', asLight=True)
			self.refreshList(lightList)
			return
		
		if type == "vrayIES":
			light = cmds.shadingNode ('VRayLightIESShape', asLight=True)
			self.refreshList(lightList)
			return
		

	def displayUI(self):

		windowName = 'LCMTUIWindow'
		if cmds.window(windowName, exists=True):
			cmds.deleteUI(windowName)
		window = cmds.window(windowName, menuBar = True,t=self.version)
		fileMenu = cmds.menu( label='Manage Light Types')
		cmds.menuItem( label='Add More Light Types',command=lambda *args:self.addLightTypes()) 
		cmds.menuItem( label='See Current Light Types', command=lambda *args:self.displayLightTypes()) 
		cmds.menuItem( label='Reset Light Types to Default Values', command=lambda *args:self.resetLightTypesToDefault()) 

		changesMenu = cmds.menu( label='Edit Multiple Light Param')
		cmds.menuItem( label='Intensity',command=lambda *args:self.changeLightParams(lightList,useGroupLights,"intensity")) 
		cmds.menuItem( label='Rename',command=lambda *args:self.changeLightParams(lightList,useGroupLights,"rename")) 

		createMenu = cmds.menu( label='Create new lights')
		cmds.menuItem( label='Area Light',command=lambda *args:self.createLight("area",lightList))
		if self.isRenderEngineInstalled('mentalRay'):
			cmds.menuItem( label='Area Light (MR)',command=lambda *args:self.createLight("areaMR",lightList)) 
		cmds.menuItem( label='Spot Light',command=lambda *args:self.createLight("spot",lightList)) 
		if self.isRenderEngineInstalled('mentalRay'):
			cmds.menuItem( label='Spot Light (MR)',command=lambda *args:self.createLight("spotMR",lightList)) 

		if self.isRenderEngineInstalled('vray'):
			cmds.menuItem( label='Rect Light (VRay)',command=lambda *args:self.createLight("vrayRect",lightList)) 
		if self.isRenderEngineInstalled('vray'):
			cmds.menuItem( label='Dome Light (VRay)',command=lambda *args:self.createLight("vrayDome",lightList)) 
		if self.isRenderEngineInstalled('vray'):
			cmds.menuItem( label='IES Light (VRay)',command=lambda *args:self.createLight("vrayIES",lightList)) 


		cmds.paneLayout( configuration='vertical2' )
		lightStageColumn = cmds.columnLayout(adjustableColumn=True)
		cmds.rowLayout(numberOfColumns = 2)
		cmds.text('Lights in the SCENE')
		cmds.button(label='Refresh!', command = lambda *args: self.refreshList(lightList))  
		cmds.setParent('..')
		print self.lightTypes
		lights = cmds.ls(dag =True,visible=True,type =self.lightTypes)  
		print "lights", lights
		lightList = cmds.iconTextScrollList(allowMultiSelection=True,  append=lights)
		cmds.rowLayout(numberOfColumns = 2)
		useGroupLights = cmds.checkBox( label='Group Lights', onCommand = lambda *args: self.updateScollList(True, lightList), offCommand = lambda *args: self.updateScollList(False, lightList))    
		cmds.checkBox( label='Save Images?', cc = lambda *args: self.toggleSaveImages())  

		cmds.setParent('..')
		cmds.iconTextScrollList(lightList,edit=True,selectCommand=lambda *args: cmds.select(self.getElementsFromLightScrollList(lightList,useGroupLights),vis=True))    
		cmds.button(label='Render Lights!', command = lambda *args: self.renderAllLights(self.getElementsFromLightScrollList(lightList,useGroupLights),cmds.checkBox(useGroupLights, query=True, value=True)))  
		cmds.text('more@nestorprado.com')   
		cmds.setParent('..')
		#new column    
		renderLayersColumn = cmds.columnLayout(adjustableColumn=True)
		cmds.text('Geometry in the SCENE')

		geometry =  cmds.ls(geometry=True)

		#take out the ibl shapes from the geo selection
		#											   Bug fix Issue #1 and #8 
		geometry = list(set(geometry) - set(lights)- set(cmds.ls(type =self.NonGeoTypes)))   

		geoList = cmds.iconTextScrollList(allowMultiSelection=True, append=geometry,selectCommand=lambda *args: cmds.select(cmds.iconTextScrollList(geoList, query=True, si=True )) )
		cmds.text('Create Render Layers from selected geometry and lights')      
		cmds.button(label='Create Render Layers!', command = lambda *args: self.createLayersFromLights(cmds.iconTextScrollList(geoList, query=True, si=True ),self.getElementsFromLightScrollList(lightList,useGroupLights)))  
		if self.isRenderEngineInstalled('vray'):
			cmds.button(label='Create Render Elements (VRay Only)', command = lambda *args: self.createRenderElementsFromLights(cmds.iconTextScrollList(geoList, query=True, si=True ),self.getElementsFromLightScrollList(lightList,useGroupLights)))  
		cmds.setParent('..')

		cmds.showWindow()

LCMT = LCMT()
LCMT.displayUI()
