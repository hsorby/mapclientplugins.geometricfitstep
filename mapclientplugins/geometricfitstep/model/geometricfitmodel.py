"""
Geometric fit model adding visualisations to github.com/ABI-Software/scaffoldfitter
"""
import os
import json

from opencmiss.maths.vectorops import add, axis_angle_to_rotation_matrix, euler_to_rotation_matrix, matrix_mult, rotation_matrix_to_euler
from opencmiss.utils.zinc.finiteelement import evaluateFieldNodesetRange
from opencmiss.utils.zinc.general import ChangeManager
from opencmiss.zinc.field import Field, FieldGroup
from opencmiss.zinc.glyph import Glyph
from opencmiss.zinc.graphics import Graphics
from opencmiss.zinc.material import Material
from opencmiss.zinc.node import Node
from opencmiss.zinc.scenefilter import Scenefilter
from scaffoldfitter.fitter import Fitter
from scaffoldfitter.fitterjson import decodeJSONFitterSteps
from scaffoldfitter.fitterstepalign import FitterStepAlign
from scaffoldfitter.fitterstepconfig import FitterStepConfig
from scaffoldfitter.fitterstepfit import FitterStepFit

from mapclientplugins.geometricfitstep.utils.zinc_utils import get_scene_selection_group, create_scene_selection_group, group_add_group_elements, group_add_group_nodes

nodeDerivativeLabels = ["D1", "D2", "D3", "D12", "D13", "D23", "D123"]


class GeometricFitModel(object):
    """
    Geometric fit model adding visualisations to github.com/ABI-Software/scaffoldfitter
    """

    def __init__(self, inputZincModelFile, inputZincDataFile, location, identifier):
        """
        :param location: Path to folder for mapclient step name.
        """
        self._fitter = Fitter(inputZincModelFile, inputZincDataFile)
        # self._fitter.setDiagnosticLevel(1)
        self._location = os.path.join(location, identifier)
        self._identifier = identifier
        self._mode_align = False
        self._align_change_callback = None
        self._initGraphicsModules()
        self._settings = {
            "displayAxes": True,
            "displayMarkerDataPoints": True,
            "displayMarkerDataNames": False,
            "displayMarkerDataProjections": True,
            "displayMarkerPoints": True,
            "displayMarkerNames": False,
            "displayDataPoints": True,
            "displayDataProjections": True,
            "displayDataProjectionPoints": True,
            "displayNodePoints": False,
            "displayNodeNumbers": False,
            "displayNodeDerivatives": False,
            "displayNodeDerivativeLabels": nodeDerivativeLabels[0:3],
            "displayElementNumbers": False,
            "displayElementAxes": False,
            "displayLines": True,
            "displayLinesExterior": False,
            "displaySurfaces": True,
            "displaySurfacesExterior": True,
            "displaySurfacesTranslucent": True,
            "displaySurfacesWireframe": False
        }
        self._loadSettings()
        self._fitter.load()
        self._currentFitterStep = self._fitter.getInitialFitterStepConfig()  # always exists

    def _initGraphicsModules(self):
        context = self._fitter.getContext()
        self._materialmodule = context.getMaterialmodule()
        with ChangeManager(self._materialmodule):
            self._materialmodule.defineStandardMaterials()
            solid_blue = self._materialmodule.createMaterial()
            solid_blue.setName("solid_blue")
            solid_blue.setManaged(True)
            solid_blue.setAttributeReal3(Material.ATTRIBUTE_AMBIENT, [0.0, 0.2, 0.6])
            solid_blue.setAttributeReal3(Material.ATTRIBUTE_DIFFUSE, [0.0, 0.7, 1.0])
            solid_blue.setAttributeReal3(Material.ATTRIBUTE_EMISSION, [0.0, 0.0, 0.0])
            solid_blue.setAttributeReal3(Material.ATTRIBUTE_SPECULAR, [0.1, 0.1, 0.1])
            solid_blue.setAttributeReal(Material.ATTRIBUTE_SHININESS, 0.2)
            trans_blue = self._materialmodule.createMaterial()
            trans_blue.setName("trans_blue")
            trans_blue.setManaged(True)
            trans_blue.setAttributeReal3(Material.ATTRIBUTE_AMBIENT, [0.0, 0.2, 0.6])
            trans_blue.setAttributeReal3(Material.ATTRIBUTE_DIFFUSE, [0.0, 0.7, 1.0])
            trans_blue.setAttributeReal3(Material.ATTRIBUTE_EMISSION, [0.0, 0.0, 0.0])
            trans_blue.setAttributeReal3(Material.ATTRIBUTE_SPECULAR, [0.1, 0.1, 0.1])
            trans_blue.setAttributeReal(Material.ATTRIBUTE_ALPHA, 0.3)
            trans_blue.setAttributeReal(Material.ATTRIBUTE_SHININESS, 0.2)
        glyphmodule = context.getGlyphmodule()
        glyphmodule.defineStandardGlyphs()
        tessellationmodule = context.getTessellationmodule()
        defaultTessellation = tessellationmodule.getDefaultTessellation()
        defaultTessellation.setRefinementFactors([12])

    def _getFitSettingsFileName(self):
        return self._location + "-settings.json"

    def _getDisplaySettingsFileName(self):
        return self._location + "-display-settings.json"

    def _loadSettings(self):
        # try:
        fitSettingsFileName = self._getFitSettingsFileName()
        if os.path.isfile(fitSettingsFileName):
            with open(fitSettingsFileName, "r") as f:
                self._fitter.decodeSettingsJSON(f.read(), decodeJSONFitterSteps)
        # except:
        #    print('_loadSettings FitSettings EXCEPTION')
        #    raise()
        # try:
        displaySettingsFileName = self._getDisplaySettingsFileName()
        if os.path.isfile(displaySettingsFileName):
            with open(displaySettingsFileName, "r") as f:
                savedSettings = json.loads(f.read())
                self._settings.update(savedSettings)
        # except:
        #    print('_loadSettings DisplaySettings EXCEPTION')
        #    pass

    def _saveSettings(self):
        with open(self._getFitSettingsFileName(), "w") as f:
            f.write(self._fitter.encodeSettingsJSON())
        with open(self._getDisplaySettingsFileName(), "w") as f:
            f.write(json.dumps(self._settings, sort_keys=False, indent=4))

    def setAlignmentChangeCallback(self, callback):
        self._align_change_callback = callback

    def getCurrentFitterStep(self):
        return self._currentFitterStep

    def setCurrentFitterStep(self, fitter_step):
        self._currentFitterStep = fitter_step

    def getCurrentFitterStepTypes(self):
        return isinstance(self._currentFitterStep, FitterStepAlign), isinstance(self._currentFitterStep, FitterStepConfig), isinstance(self._currentFitterStep, FitterStepFit)

    def addAlignStep(self):
        self._currentFitterStep = FitterStepAlign()
        self._fitter.addFitterStep(self._currentFitterStep)  # Future: , lastFitterStep

    def addConfigStep(self):
        self._currentFitterStep = FitterStepConfig()
        self._fitter.addFitterStep(self._currentFitterStep)  # Future: , lastFitterStep

    def addFitStep(self):
        self._currentFitterStep = FitterStepFit()
        self._fitter.addFitterStep(self._currentFitterStep)  # Future: , lastFitterStep

    def getOutputModelFileNameStem(self):
        return self._location

    def getOutputModelFileName(self):
        return self._location + ".exf"

    def done(self):
        self._saveSettings()
        self._fitter.run(endStep=None, modelFileNameStem=self.getOutputModelFileNameStem())
        self._fitter.writeModel(self.getOutputModelFileName())

    def getIdentifier(self):
        return self._identifier

    def getContext(self):
        return self._fitter.getContext()

    def getFitter(self):
        return self._fitter

    def getRegion(self):
        return self._fitter.getRegion()

    def getFieldmodule(self):
        return self._fitter.getFieldmodule()

    def getScene(self):
        return self._fitter.getRegion().getScene()

    def _getVisibility(self, graphicsName):
        return self._settings[graphicsName]

    def _setVisibility(self, graphicsName, show):
        self._settings[graphicsName] = show
        graphics = self.getScene().findGraphicsByName(graphicsName)
        graphics.setVisibilityFlag(show)

    def _setMultipleGraphicsVisibility(self, graphicsName, show):
        '''
        Ensure visibility of all graphics with graphicsName is set to boolean show.
        '''
        self._settings[graphicsName] = show
        scene = self.getScene()
        graphics = scene.findGraphicsByName(graphicsName)
        while graphics.isValid():
            graphics.setVisibilityFlag(show)
            while True:
                graphics = scene.getNextGraphics(graphics)
                if (not graphics.isValid()) or (graphics.getName() == graphicsName):
                    break

    def isDisplayAxes(self):
        return self._getVisibility("displayAxes")

    def setDisplayAxes(self, show):
        self._setVisibility("displayAxes", show)

    def isDisplayElementNumbers(self):
        return self._getVisibility("displayElementNumbers")

    def setDisplayElementNumbers(self, show):
        self._setVisibility("displayElementNumbers", show)

    def isDisplayLines(self):
        return self._getVisibility("displayLines")

    def setDisplayLines(self, show):
        self._setVisibility("displayLines", show)

    def isDisplayLinesExterior(self):
        return self._settings["displayLinesExterior"]

    def setDisplayLinesExterior(self, isExterior):
        self._settings["displayLinesExterior"] = isExterior
        lines = self.getScene().findGraphicsByName("displayLines")
        lines.setExterior(self.isDisplayLinesExterior())

    def isDisplayNodeDerivatives(self):
        return self._getVisibility("displayNodeDerivatives")

    def setDisplayNodeDerivatives(self, show):
        self._settings["displayNodeDerivatives"] = show
        scene = self.getScene()
        for nodeDerivativeLabel in nodeDerivativeLabels:
            graphics = scene.findGraphicsByName("displayNodeDerivatives" + nodeDerivativeLabel)
            graphics.setVisibilityFlag(show and self.isDisplayNodeDerivativeLabels(nodeDerivativeLabel))

    def isDisplayNodeDerivativeLabels(self, nodeDerivativeLabel):
        """
        :param nodeDerivativeLabel: Label from nodeDerivativeLabels ("D1", "D2" ...)
        """
        return nodeDerivativeLabel in self._settings["displayNodeDerivativeLabels"]

    def setDisplayNodeDerivativeLabels(self, nodeDerivativeLabel, show):
        """
        :param nodeDerivativeLabel: Label from nodeDerivativeLabels ("D1", "D2" ...)
        """
        shown = nodeDerivativeLabel in self._settings["displayNodeDerivativeLabels"]
        if show:
            if not shown:
                # keep in same order as nodeDerivativeLabels
                nodeDerivativeLabels = []
                for label in nodeDerivativeLabels:
                    if (label == nodeDerivativeLabel) or self.isDisplayNodeDerivativeLabels(label):
                        nodeDerivativeLabels.append(label)
                self._settings["displayNodeDerivativeLabels"] = nodeDerivativeLabels
        else:
            if shown:
                self._settings["displayNodeDerivativeLabels"].remove(nodeDerivativeLabel)
        graphics = self.getScene().findGraphicsByName("displayNodeDerivatives" + nodeDerivativeLabel)
        graphics.setVisibilityFlag(show and self.isDisplayNodeDerivatives())

    def isDisplayMarkerDataPoints(self):
        return self._getVisibility("displayMarkerDataPoints")

    def setDisplayMarkerDataPoints(self, show):
        self._setVisibility("displayMarkerDataPoints", show)

    def isDisplayMarkerDataNames(self):
        return self._getVisibility("displayMarkerDataNames")

    def setDisplayMarkerDataNames(self, show):
        self._setVisibility("displayMarkerDataNames", show)

    def isDisplayMarkerDataProjections(self):
        return self._getVisibility("displayMarkerDataProjections")

    def setDisplayMarkerDataProjections(self, show):
        self._setVisibility("displayMarkerDataProjections", show)

    def isDisplayMarkerPoints(self):
        return self._getVisibility("displayMarkerPoints")

    def setDisplayMarkerPoints(self, show):
        self._setVisibility("displayMarkerPoints", show)

    def isDisplayMarkerNames(self):
        return self._getVisibility("displayMarkerNames")

    def setDisplayMarkerNames(self, show):
        self._setVisibility("displayMarkerNames", show)

    def isDisplayDataPoints(self):
        return self._getVisibility("displayDataPoints")

    def setDisplayDataPoints(self, show):
        self._setVisibility("displayDataPoints", show)

    def isDisplayDataProjections(self):
        return self._getVisibility("displayDataProjections")

    def setDisplayDataProjections(self, show):
        self._setMultipleGraphicsVisibility("displayDataProjections", show)

    def isDisplayDataProjectionPoints(self):
        return self._getVisibility("displayDataProjectionPoints")

    def setDisplayDataProjectionPoints(self, show):
        self._setMultipleGraphicsVisibility("displayDataProjectionPoints", show)

    def isDisplayNodeNumbers(self):
        return self._getVisibility("displayNodeNumbers")

    def setDisplayNodeNumbers(self, show):
        self._setVisibility("displayNodeNumbers", show)

    def isDisplayNodePoints(self):
        return self._getVisibility("displayNodePoints")

    def setDisplayNodePoints(self, show):
        self._setVisibility("displayNodePoints", show)

    def isDisplaySurfaces(self):
        return self._getVisibility("displaySurfaces")

    def setDisplaySurfaces(self, show):
        self._setVisibility("displaySurfaces", show)

    def isDisplaySurfacesExterior(self):
        return self._settings["displaySurfacesExterior"]

    def setDisplaySurfacesExterior(self, isExterior):
        self._settings["displaySurfacesExterior"] = isExterior
        surfaces = self.getScene().findGraphicsByName("displaySurfaces")
        surfaces.setExterior(self.isDisplaySurfacesExterior() if (self._fitter.getHighestDimensionMesh().getDimension() == 3) else False)

    def isDisplaySurfacesTranslucent(self):
        return self._settings["displaySurfacesTranslucent"]

    def setDisplaySurfacesTranslucent(self, isTranslucent):
        self._settings["displaySurfacesTranslucent"] = isTranslucent
        surfaces = self.getScene().findGraphicsByName("displaySurfaces")
        surfacesMaterial = self._materialmodule.findMaterialByName("trans_blue" if isTranslucent else "solid_blue")
        surfaces.setMaterial(surfacesMaterial)

    def isDisplaySurfacesWireframe(self):
        return self._settings["displaySurfacesWireframe"]

    def setDisplaySurfacesWireframe(self, isWireframe):
        self._settings["displaySurfacesWireframe"] = isWireframe
        surfaces = self.getScene().findGraphicsByName("displaySurfaces")
        surfaces.setRenderPolygonMode(Graphics.RENDER_POLYGON_MODE_WIREFRAME if isWireframe else Graphics.RENDER_POLYGON_MODE_SHADED)

    def isDisplayElementAxes(self):
        return self._getVisibility("displayElementAxes")

    def setDisplayElementAxes(self, show):
        self._setVisibility("displayElementAxes", show)

    def needPerturbLines(self):
        """
        Return if solid surfaces are drawn with lines, requiring perturb lines to be activated.
        """
        region = self.getRegion()
        if region is None:
            return False
        mesh2d = region.getFieldmodule().findMeshByDimension(2)
        if mesh2d.getSize() == 0:
            return False
        return self.isDisplayLines() and self.isDisplaySurfaces() and not self.isDisplaySurfacesTranslucent()

    def setSelectHighlightGroup(self, group : FieldGroup):
        """
        Select and highlight objects in the group.
        :param group: FieldGroup to select, or None to clear selection.
        """
        fieldmodule = self.getFieldmodule()
        with ChangeManager(fieldmodule):
            scene = self.getScene()
            # can't use SUBELEMENT_HANDLING_MODE_FULL as some groups have been tweaked to omit some faces
            selectionGroup = get_scene_selection_group(scene, subelementHandlingMode=FieldGroup.SUBELEMENT_HANDLING_MODE_NONE)
            if group:
                if selectionGroup:
                    selectionGroup.clear()
                else:
                    selectionGroup = create_scene_selection_group(scene, subelementHandlingMode=FieldGroup.SUBELEMENT_HANDLING_MODE_NONE)
                group_add_group_elements(selectionGroup, group, highest_dimension_only=False)
                for fieldDomainType in (Field.DOMAIN_TYPE_NODES, Field.DOMAIN_TYPE_DATAPOINTS):
                    group_add_group_nodes(selectionGroup, group, fieldmodule.findNodesetByFieldDomainType(fieldDomainType))
            else:
                if selectionGroup:
                    selectionGroup.clear()
                    scene.setSelectionField(Field())

    def setSelectHighlightGroupByName(self, groupName):
        """
        Select and highlight objects in the group by name.
        :param groupName: Name of group to select, or None to clear selection.
        """
        fieldmodule = self.getFieldmodule()
        group = None
        if groupName:
            group = fieldmodule.findFieldByName(groupName).castGroup()
            if not group.isValid():
                group = None
        self.setSelectHighlightGroup(group)

    def createGraphics(self):
        fieldmodule = self.getFieldmodule()
        mesh = self._fitter.getHighestDimensionMesh()
        meshDimension = mesh.getDimension()
        modelCoordinates = self._fitter.getModelCoordinatesField()
        componentsCount = modelCoordinates.getNumberOfComponents()

        # prepare fields and calculate axis and glyph scaling
        with ChangeManager(fieldmodule):
            # fields in same order as nodeDerivativeLabels
            nodeDerivativeFields = [fieldmodule.createFieldNodeValue(modelCoordinates, derivative, 1) for derivative in [
                Node.VALUE_LABEL_D_DS1, Node.VALUE_LABEL_D_DS2, Node.VALUE_LABEL_D_DS3,
                Node.VALUE_LABEL_D2_DS1DS2, Node.VALUE_LABEL_D2_DS1DS3, Node.VALUE_LABEL_D2_DS2DS3, Node.VALUE_LABEL_D3_DS1DS2DS3]]
            elementDerivativesField = fieldmodule.createFieldConcatenate([fieldmodule.createFieldDerivative(modelCoordinates, d + 1) for d in range(meshDimension)])
            cmiss_number = fieldmodule.findFieldByName("cmiss_number")
            markerNodeGroup, markerLocation, markerCoordinates, markerName = self._fitter.getMarkerModelFields()

            # get sizing for axes
            axesScale = 1.0
            nodes = fieldmodule.findNodesetByFieldDomainType(Field.DOMAIN_TYPE_NODES)
            minX, maxX = evaluateFieldNodesetRange(modelCoordinates, nodes)
            if componentsCount == 1:
                maxRange = maxX - minX
            else:
                maxRange = maxX[0] - minX[0]
                for c in range(1, componentsCount):
                    maxRange = max(maxRange, maxX[c] - minX[c])
            if maxRange > 0.0:
                while axesScale * 10.0 < maxRange:
                    axesScale *= 10.0
                while axesScale * 0.1 > maxRange:
                    axesScale *= 0.1

            # fixed width glyph size is based on average element size in all dimensions
            mesh1d = fieldmodule.findMeshByDimension(1)
            meanLineLength = 0.0
            lineCount = mesh1d.getSize()
            if lineCount > 0:
                one = fieldmodule.createFieldConstant(1.0)
                sumLineLength = fieldmodule.createFieldMeshIntegral(one, modelCoordinates, mesh1d)
                cache = fieldmodule.createFieldcache()
                result, totalLineLength = sumLineLength.evaluateReal(cache, 1)
                glyphWidth = 0.1 * totalLineLength / lineCount
                del cache
                del sumLineLength
                del one
            if (lineCount == 0) or (glyphWidth == 0.0):
                # use function of coordinate range if no elements
                if componentsCount == 1:
                    maxScale = maxX - minX
                else:
                    first = True
                    for c in range(componentsCount):
                        scale = maxX[c] - minX[c]
                        if first or (scale > maxScale):
                            maxScale = scale
                            first = False
                if maxScale == 0.0:
                    maxScale = 1.0
                glyphWidth = 0.01 * maxScale
            glyphWidthSmall = 0.25 * glyphWidth

        # make graphics
        scene = self._fitter.getRegion().getScene()
        with ChangeManager(scene):
            scene.removeAllGraphics()

            axes = scene.createGraphicsPoints()
            pointattr = axes.getGraphicspointattributes()
            pointattr.setGlyphShapeType(Glyph.SHAPE_TYPE_AXES_XYZ)
            pointattr.setBaseSize([axesScale, axesScale, axesScale])
            pointattr.setLabelText(1, "  " + str(axesScale))
            axes.setMaterial(self._materialmodule.findMaterialByName("grey50"))
            axes.setName("displayAxes")
            axes.setVisibilityFlag(self.isDisplayAxes())

            # marker points, projections

            markerGroup = self._fitter.getMarkerGroup()
            markerDataGroup, markerDataCoordinates, markerDataName = self._fitter.getMarkerDataFields()
            markerDataLocation, markerDataLocationCoordinates, markerDataDelta = self._fitter.getMarkerDataLocationFields()
            markerNodeGroup, markerLocation, markerCoordinates, markerName = self._fitter.getMarkerModelFields()
            markerDataLocationGroupField = self._fitter.getMarkerDataLocationGroupField()

            markerDataPoints = scene.createGraphicsPoints()
            markerDataPoints.setFieldDomainType(Field.DOMAIN_TYPE_DATAPOINTS)
            if markerDataLocationGroupField:
                markerDataPoints.setSubgroupField(markerDataLocationGroupField)
            elif markerGroup:
                markerDataPoints.setSubgroupField(markerGroup)
            if markerDataCoordinates:
                markerDataPoints.setCoordinateField(markerDataCoordinates)
            pointattr = markerDataPoints.getGraphicspointattributes()
            pointattr.setBaseSize([glyphWidthSmall, glyphWidthSmall, glyphWidthSmall])
            pointattr.setGlyphShapeType(Glyph.SHAPE_TYPE_CROSS)
            markerDataPoints.setMaterial(self._materialmodule.findMaterialByName("yellow"))
            markerDataPoints.setName("displayMarkerDataPoints")
            markerDataPoints.setVisibilityFlag(self.isDisplayMarkerDataPoints())

            markerDataNames = scene.createGraphicsPoints()
            markerDataNames.setFieldDomainType(Field.DOMAIN_TYPE_DATAPOINTS)
            if markerDataLocationGroupField:
                markerDataNames.setSubgroupField(markerDataLocationGroupField)
            elif markerGroup:
                markerDataNames.setSubgroupField(markerGroup)
            if markerDataCoordinates:
                markerDataNames.setCoordinateField(markerDataCoordinates)
            pointattr = markerDataNames.getGraphicspointattributes()
            pointattr.setBaseSize([glyphWidthSmall, glyphWidthSmall, glyphWidthSmall])
            pointattr.setGlyphShapeType(Glyph.SHAPE_TYPE_NONE)
            if markerDataName:
                pointattr.setLabelField(markerDataName)
            markerDataNames.setMaterial(self._materialmodule.findMaterialByName("yellow"))
            markerDataNames.setName("displayMarkerDataNames")
            markerDataNames.setVisibilityFlag(self.isDisplayMarkerDataNames())

            markerDataProjections = scene.createGraphicsPoints()
            markerDataProjections.setFieldDomainType(Field.DOMAIN_TYPE_DATAPOINTS)
            if markerDataLocationGroupField:
                markerDataProjections.setSubgroupField(markerDataLocationGroupField)
            elif markerGroup:
                markerDataProjections.setSubgroupField(markerGroup)
            if markerDataCoordinates:
                markerDataProjections.setCoordinateField(markerDataCoordinates)
            pointAttr = markerDataProjections.getGraphicspointattributes()
            pointAttr.setGlyphShapeType(Glyph.SHAPE_TYPE_LINE)
            pointAttr.setBaseSize([0.0, 1.0, 1.0])
            pointAttr.setScaleFactors([1.0, 0.0, 0.0])
            if markerDataDelta:
                pointAttr.setOrientationScaleField(markerDataDelta)
            markerDataProjections.setMaterial(self._materialmodule.findMaterialByName("magenta"))
            markerDataProjections.setName("displayMarkerDataProjections")
            markerDataProjections.setVisibilityFlag(self.isDisplayMarkerDataProjections())

            markerPoints = scene.createGraphicsPoints()
            markerPoints.setFieldDomainType(Field.DOMAIN_TYPE_NODES)
            if markerGroup:
                markerPoints.setSubgroupField(markerGroup)
            if markerCoordinates:
                markerPoints.setCoordinateField(markerCoordinates)
            pointattr = markerPoints.getGraphicspointattributes()
            pointattr.setBaseSize([glyphWidthSmall, glyphWidthSmall, glyphWidthSmall])
            pointattr.setGlyphShapeType(Glyph.SHAPE_TYPE_CROSS)
            markerPoints.setMaterial(self._materialmodule.findMaterialByName("white"))
            markerPoints.setName("displayMarkerPoints")
            markerPoints.setVisibilityFlag(self.isDisplayMarkerPoints())

            markerNames = scene.createGraphicsPoints()
            markerNames.setFieldDomainType(Field.DOMAIN_TYPE_NODES)
            if markerGroup:
                markerNames.setSubgroupField(markerGroup)
            if markerCoordinates:
                markerNames.setCoordinateField(markerCoordinates)
            pointattr = markerNames.getGraphicspointattributes()
            pointattr.setBaseSize([glyphWidthSmall, glyphWidthSmall, glyphWidthSmall])
            pointattr.setGlyphShapeType(Glyph.SHAPE_TYPE_NONE)
            if markerName:
                pointattr.setLabelField(markerName)
            markerNames.setMaterial(self._materialmodule.findMaterialByName("white"))
            markerNames.setName("displayMarkerNames")
            markerNames.setVisibilityFlag(self.isDisplayMarkerNames())

            # data points, projections and projection points

            dataCoordinates = self._fitter.getDataCoordinatesField()
            dataPoints = scene.createGraphicsPoints()
            dataPoints.setFieldDomainType(Field.DOMAIN_TYPE_DATAPOINTS)
            if dataCoordinates:
                dataPoints.setCoordinateField(dataCoordinates)
            pointattr = dataPoints.getGraphicspointattributes()
            # pointattr.setGlyphShapeType(Glyph.SHAPE_TYPE_DIAMOND)
            # pointattr.setBaseSize([glyphWidthSmall, glyphWidthSmall, glyphWidthSmall])
            pointattr.setGlyphShapeType(Glyph.SHAPE_TYPE_POINT)
            dataPoints.setRenderPointSize(3.0)
            dataPoints.setMaterial(self._materialmodule.findMaterialByName("grey50"))
            dataPoints.setName("displayDataPoints")
            dataPoints.setVisibilityFlag(self.isDisplayDataPoints())

            for projectionMeshDimension in range(1, 3):
                dataProjectionNodeGroup = self._fitter.getDataProjectionNodeGroupField(projectionMeshDimension)
                if dataProjectionNodeGroup.getNodesetGroup().getSize() == 0:
                    continue
                dataProjectionCoordinates = self._fitter.getDataProjectionCoordinatesField(projectionMeshDimension)
                dataProjectionDelta = self._fitter.getDataProjectionDeltaField(projectionMeshDimension)
                dataProjectionError = self._fitter.getDataProjectionErrorField(projectionMeshDimension)

                dataProjections = scene.createGraphicsPoints()
                dataProjections.setFieldDomainType(Field.DOMAIN_TYPE_DATAPOINTS)
                dataProjections.setSubgroupField(dataProjectionNodeGroup)
                if dataCoordinates:
                    dataProjections.setCoordinateField(dataCoordinates)
                pointAttr = dataProjections.getGraphicspointattributes()
                pointAttr.setGlyphShapeType(Glyph.SHAPE_TYPE_LINE)
                pointAttr.setBaseSize([0.0, 1.0, 1.0])
                pointAttr.setScaleFactors([1.0, 0.0, 0.0])
                dataProjections.setRenderLineWidth(2.0 if (projectionMeshDimension == 1) else 1.0)
                if dataProjectionDelta:
                    pointAttr.setOrientationScaleField(dataProjectionDelta)
                if dataProjectionError:
                    dataProjections.setDataField(dataProjectionError)
                spectrummodule = scene.getSpectrummodule()
                spectrum = spectrummodule.getDefaultSpectrum()
                dataProjections.setSpectrum(spectrum)
                dataProjections.setName("displayDataProjections")
                dataProjections.setVisibilityFlag(self.isDisplayDataProjections())

                dataProjectionPoints = scene.createGraphicsPoints()
                dataProjectionPoints.setFieldDomainType(Field.DOMAIN_TYPE_DATAPOINTS)
                dataProjectionPoints.setSubgroupField(dataProjectionNodeGroup)
                if dataProjectionCoordinates:
                    dataProjectionPoints.setCoordinateField(dataProjectionCoordinates)
                pointattr = dataProjectionPoints.getGraphicspointattributes()
                # pointattr.setGlyphShapeType(Glyph.SHAPE_TYPE_DIAMOND)
                # pointattr.setBaseSize([glyphWidthSmall, glyphWidthSmall, glyphWidthSmall])
                pointattr.setGlyphShapeType(Glyph.SHAPE_TYPE_POINT)
                dataProjectionPoints.setRenderPointSize(3.0)
                dataProjectionPoints.setMaterial(self._materialmodule.findMaterialByName("grey50"))
                dataProjectionPoints.setName("displayDataProjectionPoints")
                dataProjectionPoints.setVisibilityFlag(self.isDisplayDataProjectionPoints())

            nodePoints = scene.createGraphicsPoints()
            nodePoints.setFieldDomainType(Field.DOMAIN_TYPE_NODES)
            nodePoints.setCoordinateField(modelCoordinates)
            pointattr = nodePoints.getGraphicspointattributes()
            pointattr.setBaseSize([glyphWidth, glyphWidth, glyphWidth])
            pointattr.setGlyphShapeType(Glyph.SHAPE_TYPE_SPHERE)
            nodePoints.setMaterial(self._materialmodule.findMaterialByName("white"))
            nodePoints.setName("displayNodePoints")
            nodePoints.setVisibilityFlag(self.isDisplayNodePoints())

            nodeNumbers = scene.createGraphicsPoints()
            nodeNumbers.setFieldDomainType(Field.DOMAIN_TYPE_NODES)
            nodeNumbers.setCoordinateField(modelCoordinates)
            pointattr = nodeNumbers.getGraphicspointattributes()
            pointattr.setLabelField(cmiss_number)
            pointattr.setGlyphShapeType(Glyph.SHAPE_TYPE_NONE)
            nodeNumbers.setMaterial(self._materialmodule.findMaterialByName("green"))
            nodeNumbers.setName("displayNodeNumbers")
            nodeNumbers.setVisibilityFlag(self.isDisplayNodeNumbers())

            # names in same order as nodeDerivativeLabels "D1", "D2", "D3", "D12", "D13", "D23", "D123" and nodeDerivativeFields
            nodeDerivativeMaterialNames = ["gold", "silver", "green", "cyan", "magenta", "yellow", "blue"]
            derivativeScales = [1.0, 1.0, 1.0, 0.5, 0.5, 0.5, 0.25]
            for i in range(len(nodeDerivativeLabels)):
                nodeDerivativeLabel = nodeDerivativeLabels[i]
                nodeDerivatives = scene.createGraphicsPoints()
                nodeDerivatives.setFieldDomainType(Field.DOMAIN_TYPE_NODES)
                nodeDerivatives.setCoordinateField(modelCoordinates)
                pointattr = nodeDerivatives.getGraphicspointattributes()
                pointattr.setGlyphShapeType(Glyph.SHAPE_TYPE_ARROW_SOLID)
                pointattr.setOrientationScaleField(nodeDerivativeFields[i])
                pointattr.setBaseSize([0.0, glyphWidth, glyphWidth])
                pointattr.setScaleFactors([derivativeScales[i], 0.0, 0.0])
                material = self._materialmodule.findMaterialByName(nodeDerivativeMaterialNames[i])
                nodeDerivatives.setMaterial(material)
                nodeDerivatives.setSelectedMaterial(material)
                nodeDerivatives.setName("displayNodeDerivatives" + nodeDerivativeLabel)
                nodeDerivatives.setVisibilityFlag(self.isDisplayNodeDerivatives() and self.isDisplayNodeDerivativeLabels(nodeDerivativeLabel))

            elementNumbers = scene.createGraphicsPoints()
            elementNumbers.setFieldDomainType(Field.DOMAIN_TYPE_MESH_HIGHEST_DIMENSION)
            elementNumbers.setCoordinateField(modelCoordinates)
            pointattr = elementNumbers.getGraphicspointattributes()
            pointattr.setLabelField(cmiss_number)
            pointattr.setGlyphShapeType(Glyph.SHAPE_TYPE_NONE)
            elementNumbers.setMaterial(self._materialmodule.findMaterialByName("cyan"))
            elementNumbers.setName("displayElementNumbers")
            elementNumbers.setVisibilityFlag(self.isDisplayElementNumbers())

            elementAxes = scene.createGraphicsPoints()
            elementAxes.setFieldDomainType(Field.DOMAIN_TYPE_MESH_HIGHEST_DIMENSION)
            elementAxes.setCoordinateField(modelCoordinates)
            pointattr = elementAxes.getGraphicspointattributes()
            pointattr.setGlyphShapeType(Glyph.SHAPE_TYPE_AXES_123)
            pointattr.setOrientationScaleField(elementDerivativesField)
            if meshDimension == 1:
                pointattr.setBaseSize([0.0, 2 * glyphWidth, 2 * glyphWidth])
                pointattr.setScaleFactors([0.25, 0.0, 0.0])
            elif meshDimension == 2:
                pointattr.setBaseSize([0.0, 0.0, 2 * glyphWidth])
                pointattr.setScaleFactors([0.25, 0.25, 0.0])
            else:
                pointattr.setBaseSize([0.0, 0.0, 0.0])
                pointattr.setScaleFactors([0.25, 0.25, 0.25])
            elementAxes.setMaterial(self._materialmodule.findMaterialByName("yellow"))
            elementAxes.setName("displayElementAxes")
            elementAxes.setVisibilityFlag(self.isDisplayElementAxes())

            lines = scene.createGraphicsLines()
            lines.setCoordinateField(modelCoordinates)
            lines.setExterior(self.isDisplayLinesExterior())
            lines.setName("displayLines")
            lines.setVisibilityFlag(self.isDisplayLines())

            surfaces = scene.createGraphicsSurfaces()
            surfaces.setCoordinateField(modelCoordinates)
            surfaces.setRenderPolygonMode(Graphics.RENDER_POLYGON_MODE_WIREFRAME if self.isDisplaySurfacesWireframe() else Graphics.RENDER_POLYGON_MODE_SHADED)
            surfaces.setExterior(self.isDisplaySurfacesExterior() if (meshDimension == 3) else False)
            surfacesMaterial = self._materialmodule.findMaterialByName("trans_blue" if self.isDisplaySurfacesTranslucent() else "solid_blue")
            surfaces.setMaterial(surfacesMaterial)
            surfaces.setName("displaySurfaces")
            surfaces.setVisibilityFlag(self.isDisplaySurfaces())

    def autorangeSpectrum(self):
        scene = self._fitter.getRegion().getScene()
        spectrummodule = scene.getSpectrummodule()
        spectrum = spectrummodule.getDefaultSpectrum()
        spectrum.autorange(scene, Scenefilter())

    # === Align Utilities ===

    def isStateAlign(self):
        return self._mode_align  # disabled as not implemented

    def setStateAlign(self, state):
        self._mode_align = state

    def rotateModel(self, axis, angle):
        mat1 = axis_angle_to_rotation_matrix(axis, angle)
        mat2 = euler_to_rotation_matrix(self._currentFitterStep.getRotation())
        new_mat = matrix_mult(mat2, mat1)
        euler = rotation_matrix_to_euler(new_mat)
        # euler = rotation_matrix_to_euler(mat1)
        # euler.reverse()
        self._currentFitterStep.setRotation(euler)
        self._currentFitterStep.run()
        self._align_change_callback()
        # self._alignSettings["euler_angles"] = rotation_matrix_to_euler(newmat)
        # self._applyAlignSettings()

    def scaleModel(self, factor):
        self._currentFitterStep.setScale(self._currentFitterStep.getScale() * factor)
        # self._currentFitterStep.setScale(factor)
        self._currentFitterStep.run()
        self._align_change_callback()
        # self._alignSettings["scale"] *= factor
        # self._applyAlignSettings()

    def offsetModel(self, relativeOffset):
        # print('relative offset:', relativeOffset)
        self._currentFitterStep.setTranslation(add(self._currentFitterStep.getTranslation(), relativeOffset))
        # self._currentFitterStep.setTranslation(relativeOffset)
        self._currentFitterStep.run()
        self._align_change_callback()
        # self._alignSettings["offset"] = add(self._currentFitterStep., relativeOffset)
        # self._applyAlignSettings()

    def _autorangeSpectrum(self):
        scene = self.getScene()
        spectrummodule = scene.getSpectrummodule()
        spectrum = spectrummodule.getDefaultSpectrum()
        scenefiltermodule = scene.getScenefiltermodule()
        scenefilter = scenefiltermodule.getDefaultScenefilter()
        spectrum.autorange(scene, scenefilter)
