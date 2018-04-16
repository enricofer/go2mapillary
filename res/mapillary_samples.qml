<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis readOnly="0" hasScaleBasedVisibilityFlag="0" minScale="1e+8" maxScale="0" simplifyDrawingTol="1" labelsEnabled="0" simplifyAlgorithm="0" simplifyDrawingHints="0" simplifyMaxScale="1" version="3.0.0-Girona" simplifyLocal="1">
  <renderer-v2 forceraster="0" enableorderby="0" symbollevels="0" type="singleSymbol">
    <symbols>
      <symbol alpha="1" name="0" clip_to_extent="1" type="marker">
        <layer enabled="1" class="SimpleMarker" pass="0" locked="0">
          <prop v="0" k="angle"/>
          <prop v="255,0,29,255" k="color"/>
          <prop v="1" k="horizontal_anchor_point"/>
          <prop v="bevel" k="joinstyle"/>
          <prop v="circle" k="name"/>
          <prop v="0,0" k="offset"/>
          <prop v="3x:0,0,0,0,0,0" k="offset_map_unit_scale"/>
          <prop v="MM" k="offset_unit"/>
          <prop v="255,0,29,77" k="outline_color"/>
          <prop v="solid" k="outline_style"/>
          <prop v="1.85" k="outline_width"/>
          <prop v="3x:0,0,0,0,0,0" k="outline_width_map_unit_scale"/>
          <prop v="MM" k="outline_width_unit"/>
          <prop v="area" k="scale_method"/>
          <prop v="2" k="size"/>
          <prop v="3x:0,0,0,0,0,0" k="size_map_unit_scale"/>
          <prop v="MM" k="size_unit"/>
          <prop v="1" k="vertical_anchor_point"/>
          <data_defined_properties>
            <Option type="Map">
              <Option value="" name="name" type="QString"/>
              <Option name="properties"/>
              <Option value="collection" name="type" type="QString"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
    </symbols>
    <rotation/>
    <sizescale/>
  </renderer-v2>
  <customproperties>
    <property key="embeddedWidgets/count" value="0"/>
    <property key="variableNames" value="mapillaryCurrentKey"/>
    <property key="variableValues" value="S7l0uby0t80jacYbws57mQ"/>
  </customproperties>
  <blendMode>0</blendMode>
  <featureBlendMode>0</featureBlendMode>
  <layerOpacity>1</layerOpacity>
  <SingleCategoryDiagramRenderer diagramType="Pie" attributeLegend="1">
    <DiagramCategory width="15" sizeScale="3x:0,0,0,0,0,0" maxScaleDenominator="1e+8" penWidth="0" enabled="0" minimumSize="0" penAlpha="255" lineSizeType="MM" penColor="#000000" lineSizeScale="3x:0,0,0,0,0,0" diagramOrientation="Up" backgroundColor="#ffffff" scaleDependency="Area" barWidth="5" sizeType="MM" scaleBasedVisibility="0" labelPlacementMethod="XHeight" backgroundAlpha="255" rotationOffset="270" height="15" minScaleDenominator="0" opacity="1">
      <fontProperties description="Ubuntu,9,-1,5,50,0,0,0,0,0" style=""/>
      <attribute color="#000000" label="" field=""/>
    </DiagramCategory>
  </SingleCategoryDiagramRenderer>
  <DiagramLayerSettings placement="0" priority="0" showAll="1" dist="0" obstacle="0" linePlacementFlags="2" zIndex="0">
    <properties>
      <Option type="Map">
        <Option value="" name="name" type="QString"/>
        <Option name="properties"/>
        <Option value="collection" name="type" type="QString"/>
      </Option>
    </properties>
  </DiagramLayerSettings>
  <fieldConfiguration>
    <field name="id">
      <editWidget type="Range">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="key">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
    <field name="note">
      <editWidget type="TextEdit">
        <config>
          <Option/>
        </config>
      </editWidget>
    </field>
  </fieldConfiguration>
  <aliases>
    <alias name="" field="id" index="0"/>
    <alias name="" field="key" index="1"/>
    <alias name="" field="note" index="2"/>
  </aliases>
  <excludeAttributesWMS/>
  <excludeAttributesWFS/>
  <defaults>
    <default expression="" field="id" applyOnUpdate="0"/>
    <default expression="" field="key" applyOnUpdate="0"/>
    <default expression="" field="note" applyOnUpdate="0"/>
  </defaults>
  <constraints>
    <constraint constraints="0" unique_strength="0" notnull_strength="0" exp_strength="0" field="id"/>
    <constraint constraints="0" unique_strength="0" notnull_strength="0" exp_strength="0" field="key"/>
    <constraint constraints="0" unique_strength="0" notnull_strength="0" exp_strength="0" field="note"/>
  </constraints>
  <constraintExpressions>
    <constraint exp="" desc="" field="id"/>
    <constraint exp="" desc="" field="key"/>
    <constraint exp="" desc="" field="note"/>
  </constraintExpressions>
  <attributeactions>
    <defaultAction key="Canvas" value="{00000000-0000-0000-0000-000000000000}"/>
  </attributeactions>
  <attributetableconfig actionWidgetStyle="dropDown" sortExpression="" sortOrder="0">
    <columns>
      <column hidden="0" width="-1" name="key" type="field"/>
      <column hidden="1" width="-1" type="actions"/>
      <column hidden="0" width="-1" name="id" type="field"/>
      <column hidden="0" width="-1" name="note" type="field"/>
    </columns>
  </attributetableconfig>
  <editform>.</editform>
  <editforminit/>
  <editforminitcodesource>0</editforminitcodesource>
  <editforminitfilepath></editforminitfilepath>
  <editforminitcode><![CDATA[# -*- coding: utf-8 -*-
"""
I form QGIS possono avere una funzione Python che può essere chiamata quando un form viene aperto.

Usa questa funzione per aggiungere logica extra ai tuoi forms..

Inserisci il nome della funzione nel campo "Funzione Python di avvio".

Segue un esempio:
"""
from qgis.PyQt.QtWidgets import QWidget

def my_form_open(dialog, layer, feature):
	geom = feature.geometry()
	control = dialog.findChild(QWidget, "MyLineEdit")
]]></editforminitcode>
  <featformsuppress>0</featformsuppress>
  <editorlayout>generatedlayout</editorlayout>
  <editable>
    <field editable="1" name="ca"/>
    <field editable="1" name="captured_at"/>
    <field editable="1" name="id"/>
    <field editable="1" name="key"/>
    <field editable="1" name="note"/>
    <field editable="1" name="pano"/>
    <field editable="1" name="skey"/>
    <field editable="1" name="userkey"/>
  </editable>
  <labelOnTop>
    <field labelOnTop="0" name="ca"/>
    <field labelOnTop="0" name="captured_at"/>
    <field labelOnTop="0" name="id"/>
    <field labelOnTop="0" name="key"/>
    <field labelOnTop="0" name="note"/>
    <field labelOnTop="0" name="pano"/>
    <field labelOnTop="0" name="skey"/>
    <field labelOnTop="0" name="userkey"/>
  </labelOnTop>
  <widgets/>
  <conditionalstyles>
    <rowstyles/>
    <fieldstyles/>
  </conditionalstyles>
  <expressionfields/>
  <previewExpression>skey</previewExpression>
  <mapTip>location</mapTip>
  <layerGeometryType>0</layerGeometryType>
</qgis>
