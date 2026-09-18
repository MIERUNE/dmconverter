<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis styleCategories="Symbology|Fields|Forms" version="3.42.1-Münster">
  <renderer-v2 attr="HCODE2" type="categorizedSymbol" symbollevels="0" forceraster="0" enableorderby="0" referencescale="-1">
    <categories>
      <category value="352200" label="寺院" render="true" type="string" symbol="0"/>
      <category value="300100" label="普通建物" render="true" type="string" symbol="1"/>
    </categories>
    <symbols>
      <symbol type="marker" name="0" alpha="1" clip_to_extent="1" force_rhr="0">
        <layer class="SimpleMarker" enabled="1" locked="0" pass="0">
          <Option type="Map">
            <Option name="name" type="QString" value="circle"/>
            <Option name="color" type="QString" value="255,0,0,255"/>
            <Option name="size" type="QString" value="2"/>
            <Option name="size_unit" type="QString" value="MM"/>
          </Option>
        </layer>
      </symbol>
      <symbol type="marker" name="1" alpha="1" clip_to_extent="1" force_rhr="0">
        <layer class="SimpleMarker" enabled="1" locked="0" pass="0">
          <Option type="Map">
            <Option name="name" type="QString" value="circle"/>
            <Option name="color" type="QString" value="0,0,255,255"/>
            <Option name="size" type="QString" value="2"/>
            <Option name="size_unit" type="QString" value="MM"/>
          </Option>
        </layer>
      </symbol>
    </symbols>
    <rotation/>
    <sizescale/>
  </renderer-v2>
  <fieldConfiguration>
    <field name="HCODE2" configurationFlags="NoFlag">
      <editWidget type="ValueMap">
        <config>
          <Option type="Map">
            <Option name="map" type="List">
              <Option type="Map">
                <Option name="未入力（NULL）" type="QString" value="{2839923C-8B7D-419E-B84B-CA2FE9B80EC7}"/>
              </Option>
              <Option type="Map">
                <Option name="352200:寺院" type="QString" value="352200"/>
              </Option>
              <Option type="Map">
                <Option name="300100:普通建物" type="QString" value="300100"/>
              </Option>
            </Option>
          </Option>
        </config>
      </editWidget>
    </field>
    <field name="分類コード" configurationFlags="NoFlag">
      <editWidget type="TextEdit">
        <config>
          <Option type="Map">
            <Option name="IsMultiline" type="bool" value="false"/>
            <Option name="UseHtml" type="bool" value="false"/>
          </Option>
        </config>
      </editWidget>
    </field>
    <field name="字の大きさ" configurationFlags="NoFlag">
      <editWidget type="Range">
        <config>
          <Option type="Map">
            <Option name="AllowNull" type="bool" value="true"/>
            <Option name="Max" type="int" value="99999"/>
            <Option name="Min" type="int" value="1"/>
            <Option name="Step" type="int" value="1"/>
            <Option name="Style" type="QString" value="SpinBox"/>
          </Option>
        </config>
      </editWidget>
    </field>
  </fieldConfiguration>
  <aliases>
    <alias field="HCODE2" index="0" name="地物コード（HCODE2）"/>
    <alias field="分類コード" index="1" name=""/>
    <alias field="字の大きさ" index="2" name="字の大きさ（0.1 mm単位）"/>
  </aliases>
  <defaults>
    <default field="HCODE2" applyOnUpdate="0" expression=""/>
    <default field="分類コード" applyOnUpdate="1" expression="left(&quot;HCODE2&quot;, 4)"/>
    <default field="字の大きさ" applyOnUpdate="0" expression=""/>
  </defaults>
  <constraints>
    <constraint field="HCODE2" constraints="0" notnull_strength="0" unique_strength="0" exp_strength="0"/>
    <constraint field="分類コード" constraints="0" notnull_strength="0" unique_strength="0" exp_strength="0"/>
    <constraint field="字の大きさ" constraints="4" notnull_strength="0" unique_strength="0" exp_strength="1"/>
  </constraints>
  <constraintExpressions>
    <constraint field="HCODE2" desc="" exp=""/>
    <constraint field="分類コード" desc="" exp=""/>
    <constraint field="字の大きさ" desc="1以上" exp="&quot;字の大きさ&quot; IS NULL OR &quot;字の大きさ&quot; >= 1"/>
  </constraintExpressions>
  <editform tolerant="1"></editform>
  <featformsuppress>0</featformsuppress>
  <editorlayout>generatedlayout</editorlayout>
  <editable>
    <field name="分類コード" editable="0"/>
  </editable>
  <labelOnTop>
    <field name="HCODE2" labelOnTop="1"/>
  </labelOnTop>
  <reuseLastValue/>
  <layerGeometryType>0</layerGeometryType>
</qgis>
