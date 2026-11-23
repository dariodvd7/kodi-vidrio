"""Genera skin.vidrio/xml/Custom_1154_VidrioGuia.xml: la guía de TV (una fila de canales por grupo).

Uso: python3 guia_ventana.py ../skin.vidrio/xml/Custom_1154_VidrioGuia.xml  (escribe también Includes_Guia.xml)
"""
import sys

GRUPOS = ['Aire', 'Noticias', 'Deportes', 'Películas y series', 'Infantiles', 'Documentales', 'Música',
          'Internacionales', 'Otros']
FILAS = [(5601 + i, g) for i, g in enumerate(GRUPOS)]
# Android: DGO acepta enlaces dtvmobile:// (DeepLinkKt.processDeepLink en su app): dtvmobile://live abre la pestaña
# TV en vivo (su grilla). Un canal puntual pide el identificador interno de DGO, que solo da su API privada.
ABRIR = 'StartAndroidActivity(com.directv.dtvlatam,android.intent.action.VIEW,,dtvmobile://live)'
# tvOS: Kodi no abre apps, pero el servicio de Vidrio pide a tvOS (ctypes + openURL) la página de DGO en la App Store,
# que queda con el foco en "Abrir": un clic más y entra a DGO. DGO no tiene un enlace propio que tvOS acepte.
ABRIR_TVOS = 'RunPlugin(plugin://plugin.video.vidrio/?abrir=itms-apps%3A%2F%2Fapps.apple.com%2Far%2Fapp%2Fid1349939060)'


def var(nombre, plantilla, defecto=''):
    out = [f'\t\t<variable name="{nombre}">']
    for cid, _ in FILAS:
        out.append(f'\t\t\t<value condition="Control.HasFocus({cid})">{plantilla.format(c=f"Container({cid}).")}</value>')
    for cid, _ in FILAS:  # sin foco en las filas: lo último visto en la primera fila con canales
        out.append(f'\t\t\t<value condition="Integer.IsGreater(Container({cid}).NumItems,0)">{plantilla.format(c=f"Container({cid}).")}</value>')
    out.append(f'\t\t\t<value>{defecto}</value>')
    out.append('\t\t</variable>')
    return '\n'.join(out)


def tarjeta(cid, foco):
    zoom = (f'\t\t\t\t\t\t<animation effect="zoom" start="100" end="108" center="160,95" time="200" tween="cubic" '
            f'easing="out" reversible="false" condition="Control.HasFocus({cid})">Conditional</animation>\n') if foco else ''
    borde = (f'\t\t\t\t\t\t<control type="image"><width>320</width><height>190</height><texture>vidrio/card_focus.png</texture>'
             f'<visible>Control.HasFocus({cid})</visible></control>\n') if foco else ''
    color = 'FFFFFFFF' if foco else 'D9FFFFFF'
    return f'''\t\t\t\t\t<control type="group">
						<left>14</left><top>16</top>
{zoom}						<control type="image"><width>320</width><height>190</height><texture border="30">vidrio/glass_nofo.png</texture></control>
						<control type="image">
							<left>60</left><top>30</top><width>200</width><height>110</height>
							<aspectratio>keep</aspectratio>
							<texture background="true">$INFO[ListItem.Art(thumb)]</texture>
						</control>
						<control type="label">
							<left>20</left><top>60</top><width>280</width><height>60</height><align>center</align><aligny>center</aligny>
							<font>vidrio_row</font><textcolor>F2FFFFFF</textcolor>
							<label>$INFO[ListItem.Label]</label>
							<visible>String.IsEmpty(ListItem.Art(thumb))</visible>
						</control>
						<control type="progress">
							<left>24</left><top>166</top><width>272</width><height>6</height>
							<texturebg border="3" colordiffuse="40FFFFFF">vidrio/pill_focus.png</texturebg>
							<lefttexture/><righttexture/>
							<midtexture border="3">vidrio/pill_focus.png</midtexture>
							<info>ListItem.PercentPlayed</info>
						</control>
{borde}					</control>
					<control type="label">
						<left>20</left><top>214</top><width>310</width><height>34</height>
						<font>vidrio_small</font><textcolor>{color}</textcolor>
						{'<scroll>true</scroll>' if foco else ''}
						<label>$INFO[ListItem.Property(vidrio.ahora)]</label>
					</control>
'''


def barra(cid):
    return f'''				<control type="progress">
					<width>700</width><height>8</height>
					<texturebg border="4" colordiffuse="40FFFFFF">vidrio/pill_focus.png</texturebg>
					<lefttexture/><righttexture/>
					<midtexture border="4">vidrio/pill_focus.png</midtexture>
					<info>Container({cid}).ListItem.PercentPlayed</info>
					<visible>Control.HasFocus({cid}) | [!Control.HasFocus(5601) + !Control.HasFocus(5602) + !Control.HasFocus(5603) + !Control.HasFocus(5604) + !Control.HasFocus(5605) + !Control.HasFocus(5606) + !Control.HasFocus(5607) + !Control.HasFocus(5608) + !Control.HasFocus(5609) + String.IsEqual({cid},5601)]</visible>
				</control>
'''


def fila(i, cid, grupo):
    arriba = 'SetFocus(5690)' if i == 0 else f'{FILAS[i - 1][0]}'
    abajo = f'{FILAS[i + 1][0]}' if i + 1 < len(FILAS) else f'{cid}'
    return f'''			<control type="group">
				<height>300</height>
				<visible>Integer.IsGreater(Container({cid}).NumItems,0) | Container({cid}).IsUpdating</visible>
				<control type="label">
					<left>110</left><width>800</width><height>44</height>
					<font>vidrio_row</font><textcolor>F2FFFFFF</textcolor>
					<label>{grupo}</label>
				</control>
				<control type="list" id="{cid}">
					<left>90</left><top>40</top><width>1830</width><height>260</height>
					<orientation>horizontal</orientation>
					<scrolltime tween="cubic" easing="out">300</scrolltime>
					{'<onup>5690</onup>' if i == 0 else f'<onup>{arriba}</onup>'}
					<ondown>{abajo}</ondown>
					<onclick condition="System.Platform.Android">{ABRIR}</onclick>
					<onclick condition="!System.Platform.Android">{ABRIR_TVOS}</onclick>
					<itemlayout width="350" height="260">
{tarjeta(cid, False)}					</itemlayout>
					<focusedlayout width="350" height="260">
{tarjeta(cid, True)}					</focusedlayout>
					<content target="videos">plugin://plugin.video.vidrio/?lista=guia&amp;grupo={grupo.replace(' ', '%20')}&amp;h=$INFO[System.Time(hh)]</content>
				</control>
			</control>
'''


xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<!--
	Vidrio: guía de TV (generada por herramientas/guia_ventana.py; no editar a mano).
	Datos: guia.json del homelab (homelab/guia.py, open-epg.com). Arriba, el programa del canal con foco; abajo, una
	fila de canales por grupo. Elegir un canal (o "Abrir DGO") abre DGO: en Android directo, en el Apple TV la página
	de DGO en la App Store con el foco en "Abrir".
-->
<window id="1154" type="window">
	<defaultcontrol always="true">5600</defaultcontrol>
	<backgroundcolor>FF0A0A0E</backgroundcolor>
	<controls>
		<control type="image">
			<left>0</left><top>0</top><width>1920</width><height>1080</height>
			<texture colordiffuse="FF0A0A0E">vidrio/white.png</texture>
		</control>
		<control type="image">
			<left>0</left><top>0</top><width>1920</width><height>640</height>
			<texture colordiffuse="FF16213A">vidrio/white.png</texture>
		</control>
		<control type="image">
			<left>0</left><top>200</top><width>1920</width><height>460</height>
			<texture>vidrio/fade_bottom.png</texture>
		</control>

		<!-- Encabezado -->
		<control type="label">
			<left>110</left><top>44</top><width>900</width><height>60</height>
			<font>vidrio_row</font><textcolor>F2FFFFFF</textcolor>
			<label>Guía de TV</label>
		</control>
		<control type="button" id="5690">
			<right>420</right><top>44</top><width>260</width><height>60</height>
			<font>vidrio_tab</font><label>Abrir DGO</label>
			<align>center</align><aligny>center</aligny>
			<textcolor>E6FFFFFF</textcolor><focusedcolor>FF101014</focusedcolor>
			<texturefocus border="30">vidrio/pill_focus.png</texturefocus>
			<texturenofocus border="30">vidrio/glass_pill.png</texturenofocus>
			<onclick condition="System.Platform.Android">{ABRIR}</onclick>
			<onclick condition="!System.Platform.Android">{ABRIR_TVOS}</onclick>
			<ondown>5600</ondown>
		</control>
		<control type="label">
			<right>80</right><top>48</top><width>300</width><height>52</height>
			<align>right</align><aligny>center</aligny>
			<font>vidrio_tab</font><textcolor>E6FFFFFF</textcolor>
			<label>$INFO[System.Time]</label>
		</control>

		<!-- Programa del canal con foco -->
		<control type="group">
			<left>110</left><top>130</top>
			<control type="image">
				<left>1400</left><top>0</top><width>300</width><height>170</height>
				<aspectratio>keep</aspectratio>
				<texture background="true">$VAR[GuiaLogo]</texture>
			</control>
			<control type="label">
				<width>1250</width><height>36</height>
				<font>vidrio_kicker</font><textcolor>B3FFFFFF</textcolor>
				<label>$VAR[GuiaCanal]</label>
			</control>
			<control type="label">
				<top>36</top><width>1250</width><height>90</height>
				<font>vidrio_hero</font><textcolor>FFFFFFFF</textcolor>
				<label>$VAR[GuiaAhora]</label>
			</control>
			<control type="label">
				<top>130</top><width>1250</width><height>40</height>
				<font>vidrio_meta</font><textcolor>D9FFFFFF</textcolor>
				<label>$VAR[GuiaHorario]</label>
			</control>
			<control type="group">
				<top>182</top>
{''.join(barra(cid) for cid, _ in FILAS)}
			</control>
			<control type="textbox">
				<top>210</top><width>1150</width><height>120</height>
				<font>vidrio_plot</font><textcolor>CCFFFFFF</textcolor>
				<label>$VAR[GuiaSinopsis]</label>
			</control>
			<control type="label">
				<top>340</top><width>1250</width><height>36</height>
				<font>vidrio_small</font><textcolor>99FFFFFF</textcolor>
				<label>$VAR[GuiaSiguiente]</label>
			</control>
		</control>

		<!-- Filas de canales -->
		<control type="grouplist" id="5600">
			<left>0</left><top>530</top><width>1920</width><height>550</height>
			<orientation>vertical</orientation>
			<itemgap>0</itemgap>
			<scrolltime tween="cubic" easing="out">350</scrolltime>
{''.join(fila(i, cid, g) for i, (cid, g) in enumerate(FILAS))}		</control>
	</controls>
</window>
'''
open(sys.argv[1], 'w', encoding='utf-8').write(xml)
variables = '\n'.join([
    var('GuiaCanal', '$INFO[{c}ListItem.Label]$INFO[{c}ListItem.Property(vidrio.grupo),  ·  ,]', 'Guía de TV'),
    var('GuiaAhora', '$INFO[{c}ListItem.Property(vidrio.ahora)]'),
    var('GuiaHorario', '$INFO[{c}ListItem.Property(vidrio.horario)]$INFO[{c}ListItem.Property(vidrio.quedan),   ·   ,]'),
    var('GuiaSinopsis', '$INFO[{c}ListItem.Plot]'),
    var('GuiaSiguiente', '$INFO[{c}ListItem.Property(vidrio.siguiente),Después:  ,]'),
    var('GuiaLogo', '$INFO[{c}ListItem.Art(thumb)]'),
]).replace('\n\t\t', '\n\t')
incluye = sys.argv[1].replace('Custom_1154_VidrioGuia.xml', 'Includes_Guia.xml')
open(incluye, 'w', encoding='utf-8').write('<?xml version="1.0" encoding="UTF-8"?>\n'
    '<!-- Generado por herramientas/guia_ventana.py: variables de la guía de TV. -->\n<includes>\n'
    + variables.replace('\t\t<variable', '\t<variable') + '\n</includes>\n')
print('ok')
