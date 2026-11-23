"""Genera xml/Includes_Vidrio.xml (variables repetidas por fila)."""
import sys
FILAS = range(5100, 5109)  # 5100 = Continuar viendo (Trakt)

def var(nombre, plantilla, defecto=None):
    out = [f'\t<variable name="{nombre}">']
    for i in FILAS:
        out.append(f'\t\t<value condition="Control.HasFocus({i})">{plantilla.format(c=f"Container({i}).")}</value>')
    for i in FILAS:  # sin foco en filas (barra de arriba): el último elemento visto de la primera fila con contenido
        out.append(f'\t\t<value condition="Integer.IsGreater(Container({i}).NumItems,0)">{plantilla.format(c=f"Container({i}).")}</value>')
    if defecto is not None:
        out.append(f'\t\t<value>{defecto}</value>')
    out.append('\t</variable>')
    return '\n'.join(out)

partes = [
    var('VidrioFanart', '$INFO[{c}ListItem.Art(fanart)]'),
    var('VidrioTitulo', '$INFO[{c}ListItem.Label]'),
    var('VidrioMeta', '$INFO[{c}ListItem.Property(vidrio.meta)]'),
    var('VidrioSinopsis', '$INFO[{c}ListItem.Plot]'),
    var('VidrioKicker', '$INFO[{c}ListItem.Property(vidrio.etiqueta)]$INFO[{c}ListItem.Rating,   ★ ,]'),
    var('VidrioTipo', '$INFO[{c}ListItem.Property(vidrio.tipo)]'),
    var('VidrioTrailer', '$INFO[{c}ListItem.Property(vidrio.trailer)]'),
]
def cond_var(nombre, casos, defecto=''):
    out = [f'\t<variable name="{nombre}">']
    for cond, valor in casos:
        for i in FILAS:
            c = f'Container({i}).'
            out.append(f'\t\t<value condition="Control.HasFocus({i}) + {cond.format(c=c)}">{valor}</value>')
    if defecto:
        out.append(f'\t\t<value>{defecto}</value>')
    out.append('\t</variable>')
    return '\n'.join(out)

accion = cond_var('VidrioAccion', [('String.IsEqual({c}ListItem.Property(vidrio.continuar),1)', 'Continuar'),
                                      ('String.IsEqual({c}ListItem.Property(vidrio.tipo),serie)', 'Episodios')], 'Ver')
hint = ('\t<variable name="VidrioTrailerHint">\n'
        '\t\t<value condition="!String.IsEmpty(Window(home).Property(Vidrio.Preview)) + Player.HasVideo">Reproduciendo el tráiler</value>\n'
        + '\n'.join(f'\t\t<value condition="Control.HasFocus({i}) + !String.IsEmpty(Container({i}).ListItem.Property(vidrio.trailer)) + !Player.HasVideo">El tráiler empieza en unos segundos</value>' for i in FILAS)
        + '\n\t</variable>')

xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<!-- Generado por herramientas/includes.py: no editar a mano las variables por fila. -->
<includes>
{chr(10).join(partes)}
{accion}
{hint}

	<variable name="VidrioFichaKicker">
		<value condition="!String.IsEmpty(ListItem.Property(vidrio.etiqueta))">$INFO[ListItem.Property(vidrio.etiqueta)]$INFO[ListItem.Rating,   ★ ,]</value>
		<value condition="String.IsEqual(ListItem.DBType,tvshow)">SERIE$INFO[ListItem.Rating,   ★ ,]</value>
		<value condition="String.IsEqual(ListItem.DBType,episode)">EPISODIO$INFO[ListItem.Rating,   ★ ,]</value>
		<value>PELÍCULA$INFO[ListItem.Rating,   ★ ,]</value>
	</variable>
	<variable name="VidrioFichaMeta">
		<value condition="!String.IsEmpty(ListItem.Property(vidrio.meta))">$INFO[ListItem.Property(vidrio.meta)]</value>
		<value>$INFO[ListItem.Year]$INFO[ListItem.Genre,  ·  ,]$INFO[ListItem.Duration,  ·  , min]</value>
	</variable>

	<include name="VidrioDato">
		<param name="nombre"/><param name="info"/><param name="sufijo"/>
		<definition>
			<control type="group">
				<height>36</height>
				<visible>!String.IsEmpty($PARAM[info])</visible>
				<control type="label">
					<width>170</width><height>36</height>
					<font>vidrio_small</font><textcolor>8CFFFFFF</textcolor>
					<label>$PARAM[nombre]</label>
				</control>
				<control type="label">
					<left>176</left><width>276</width><height>36</height>
					<font>vidrio_small</font><textcolor>F2FFFFFF</textcolor>
					<label>$INFO[$PARAM[info]]$PARAM[sufijo]</label>
				</control>
			</control>
		</definition>
	</include>

	<include name="VidrioBoton">
		<param name="id"/><param name="label"/><param name="visible"/>
		<definition>
			<control type="button" id="$PARAM[id]">
				<width>auto</width><height>72</height>
				<font>vidrio_tab</font>
				<label>$PARAM[label]</label>
				<align>center</align><aligny>center</aligny>
				<textoffsetx>44</textoffsetx>
				<textcolor>FFFFFFFF</textcolor>
				<focusedcolor>FF101014</focusedcolor>
				<texturefocus border="36">vidrio/pill_focus.png</texturefocus>
				<texturenofocus border="36">vidrio/glass_pill.png</texturenofocus>
				<visible>$PARAM[visible]</visible>
			</control>
		</definition>
	</include>

	<include name="VidrioEpisodio">
		<!-- Tarjeta de episodio: captura arriba (Jellyfin), datos abajo. Dentro de un panel de vidrio de 500x450. -->
		<control type="image">
			<left>14</left><top>14</top><width>472</width><height>266</height>
			<aspectratio>scale</aspectratio>
			<texture background="true" diffuse="vidrio/mask_card.png" fallback="vidrio/white.png">$INFO[ListItem.Art(thumb)]</texture>
		</control>
		<control type="label">
			<left>30</left><top>292</top><width>300</width><height>32</height>
			<font>vidrio_kicker</font><textcolor>B3FFFFFF</textcolor>
			<label>$INFO[ListItem.Property(vidrio.numero)]</label>
		</control>
		<control type="label">
			<left>270</left><top>292</top><width>200</width><height>32</height>
			<align>right</align>
			<font>vidrio_small</font><textcolor>99FFFFFF</textcolor>
			<label>$INFO[ListItem.Property(vidrio.duracion)]</label>
		</control>
		<control type="label">
			<left>30</left><top>326</top><width>440</width><height>40</height>
			<font>vidrio_row</font><textcolor>FFFFFFFF</textcolor>
			<label>$INFO[ListItem.Property(vidrio.titulo)]</label>
		</control>
		<control type="textbox">
			<left>30</left><top>370</top><width>440</width><height>66</height>
			<font>vidrio_small</font><textcolor>BFFFFFFF</textcolor>
			<label>$INFO[ListItem.Plot]</label>
			<visible>!String.IsEmpty(ListItem.Property(vidrio.titulo))</visible>
		</control>
		<control type="textbox">
			<left>30</left><top>330</top><width>440</width><height>100</height>
			<font>vidrio_small</font><textcolor>BFFFFFFF</textcolor>
			<label>$INFO[ListItem.Plot]</label>
			<visible>String.IsEmpty(ListItem.Property(vidrio.titulo))</visible>
		</control>
	</include>

	<variable name="VidrioBusquedaTitulo">
		<value condition="String.IsEmpty(Control.GetLabel(5401).index(1))">Agregadas recientemente</value>
		<value condition="Integer.IsEqual(Container(5402).NumItems,1)">1 resultado</value>
		<value condition="Integer.IsGreater(Container(5402).NumItems,1)">$INFO[Container(5402).NumItems] resultados</value>
	</variable>
	<variable name="VidrioGrillaTitulo">
		<value condition="!String.IsEmpty(Window(home).Property(Vidrio.GrillaTitulo))">$INFO[Window(home).Property(Vidrio.GrillaTitulo)]</value>
		<value>Películas</value>
	</variable>

	<include name="VidrioOrden">
		<!-- Píldora de orden de la grilla: dos botones (elegido / no elegido) según Vidrio.GrillaOrden -->
		<param name="id"/><param name="label"/><param name="orden"/>
		<definition>
			<control type="button" id="$PARAM[id]">
				<width>auto</width><height>64</height>
				<font>vidrio_tab</font><label>$PARAM[label]</label>
				<align>center</align><aligny>center</aligny><textoffsetx>34</textoffsetx>
				<textcolor>FFFFFFFF</textcolor><focusedcolor>FF101014</focusedcolor>
				<texturefocus border="32">vidrio/pill_focus.png</texturefocus>
				<texturenofocus border="30">vidrio/glass_panel_focus.png</texturenofocus>
				<onclick>SetProperty(Vidrio.GrillaOrden,$PARAM[orden],home)</onclick>
				<visible>String.IsEqual(Window(home).Property(Vidrio.GrillaOrden),$PARAM[orden])</visible>
			</control>
			<control type="button" id="$PARAM[id]0">
				<width>auto</width><height>64</height>
				<font>vidrio_tab</font><label>$PARAM[label]</label>
				<align>center</align><aligny>center</aligny><textoffsetx>34</textoffsetx>
				<textcolor>D9FFFFFF</textcolor><focusedcolor>FF101014</focusedcolor>
				<texturefocus border="32">vidrio/pill_focus.png</texturefocus>
				<texturenofocus border="32">vidrio/glass_pill.png</texturenofocus>
				<onclick>SetProperty(Vidrio.GrillaOrden,$PARAM[orden],home)</onclick>
				<visible>!String.IsEqual(Window(home).Property(Vidrio.GrillaOrden),$PARAM[orden])</visible>
			</control>
		</definition>
	</include>

	<variable name="VidrioOSDKicker">
		<value condition="!String.IsEmpty(VideoPlayer.TVShowTitle)">$INFO[VideoPlayer.TVShowTitle]$INFO[VideoPlayer.Season,  ·  T,]$INFO[VideoPlayer.Episode, E,]</value>
		<value>$INFO[VideoPlayer.Year]$INFO[VideoPlayer.Genre,  ·  ,]</value>
	</variable>
	<variable name="VidrioOSDPausa">
		<value condition="Player.Paused">Reproducir</value>
		<value>Pausa</value>
	</variable>
	<variable name="VidrioOSDPistas">
		<value condition="VideoPlayer.SubtitlesEnabled">Audio: $INFO[VideoPlayer.AudioLanguage]$INFO[VideoPlayer.AudioCodec,  ,]$INFO[VideoPlayer.AudioChannels, , canales]      Subtítulos: $INFO[VideoPlayer.SubtitlesLanguage]</value>
		<value>Audio: $INFO[VideoPlayer.AudioLanguage]$INFO[VideoPlayer.AudioCodec,  ,]$INFO[VideoPlayer.AudioChannels, , canales]      Subtítulos: desactivados</value>
	</variable>

	<include name="VidrioBotonOSD">
		<param name="id"/><param name="label"/><param name="accion"/>
		<param name="accion2" default="noop"/><param name="accion3" default="noop"/><param name="visible" default="true"/>
		<definition>
			<control type="button" id="$PARAM[id]">
				<width>auto</width><height>72</height>
				<font>vidrio_tab</font><label>$PARAM[label]</label>
				<align>center</align><aligny>center</aligny><textoffsetx>36</textoffsetx>
				<textcolor>FFFFFFFF</textcolor><focusedcolor>FF101014</focusedcolor>
				<texturefocus border="36">vidrio/pill_focus.png</texturefocus>
				<texturenofocus border="36">vidrio/glass_pill.png</texturenofocus>
				<onclick>$PARAM[accion]</onclick>
				<onclick>$PARAM[accion2]</onclick>
				<onclick>$PARAM[accion3]</onclick>
				<visible>$PARAM[visible]</visible>
			</control>
		</definition>
	</include>

	<include name="VidrioAjustesPanel">
		<!-- Tarjetas de vidrio de la pantalla de ajustes -->
		<param name="id"/>
		<definition>
		<scrolltime tween="cubic" easing="out">250</scrolltime>
		<itemlayout width="420" height="230">
			<control type="image">
				<left>14</left><top>10</top><width>392</width><height>206</height>
				<texture border="30">vidrio/glass_panel.png</texture>
			</control>
			<control type="image">
				<left>40</left><top>40</top><width>72</width><height>72</height>
				<aspectratio>keep</aspectratio>
				<texture colordiffuse="D9FFFFFF">$INFO[ListItem.Icon]</texture>
			</control>
			<control type="label">
				<left>40</left><top>126</top><width>340</width><height>40</height>
				<font>vidrio_tab</font><textcolor>F2FFFFFF</textcolor>
				<label>$INFO[ListItem.Label]</label>
			</control>
			<control type="label">
				<left>40</left><top>166</top><width>340</width><height>32</height>
				<font>vidrio_small</font><textcolor>8CFFFFFF</textcolor>
				<label>$INFO[ListItem.Label2]</label>
			</control>
		</itemlayout>
		<focusedlayout width="420" height="230">
			<control type="group">
				<animation effect="zoom" start="100" end="105" center="210,113" time="200" tween="cubic" easing="out" reversible="false" condition="Control.HasFocus($PARAM[id])">Conditional</animation>
				<control type="image">
					<left>14</left><top>10</top><width>392</width><height>206</height>
					<texture border="30">vidrio/glass_panel_focus.png</texture>
				</control>
				<control type="image">
					<left>14</left><top>10</top><width>392</width><height>206</height>
					<texture border="30">vidrio/card_focus_panel.png</texture>
					<visible>Control.HasFocus($PARAM[id])</visible>
				</control>
				<control type="image">
					<left>40</left><top>40</top><width>72</width><height>72</height>
					<aspectratio>keep</aspectratio>
					<texture>$INFO[ListItem.Icon]</texture>
				</control>
				<control type="label">
					<left>40</left><top>126</top><width>340</width><height>40</height>
					<font>vidrio_tab</font><textcolor>FFFFFFFF</textcolor>
					<label>$INFO[ListItem.Label]</label>
				</control>
				<control type="label">
					<left>40</left><top>166</top><width>340</width><height>32</height>
					<font>vidrio_small</font><textcolor>B3FFFFFF</textcolor>
					<label>$INFO[ListItem.Label2]</label>
				</control>
			</control>
		</focusedlayout>
		</definition>
	</include>

	<include name="VidrioTab">
		<param name="id"/><param name="label"/><param name="action"/><param name="previo" default="noop"/><param name="previo2" default="noop"/>
		<param name="visible" default="true"/>
		<definition>
			<control type="button" id="$PARAM[id]">
				<visible>$PARAM[visible]</visible>
				<width>auto</width><height>64</height>
				<font>vidrio_tab</font>
				<label>$PARAM[label]</label>
				<align>center</align><aligny>center</aligny>
				<textoffsetx>22</textoffsetx>
				<textcolor>E6FFFFFF</textcolor>
				<focusedcolor>FF101014</focusedcolor>
				<texturefocus border="32">vidrio/pill_focus.png</texturefocus>
				<texturenofocus/>
				<onclick>$PARAM[previo]</onclick>
				<onclick>$PARAM[previo2]</onclick>
				<onclick>$PARAM[action]</onclick>
				<onback>Quit</onback>
			</control>
		</definition>
	</include>

	<include name="VidrioFila">
		<param name="id"/><param name="titulo"/><param name="ruta"/><param name="arriba"/><param name="abajo"/>
		<param name="arriba_si" default="true"/><param name="arriba_no" default="noop"/>
		<param name="tambien" default="false"/>
		<definition>
			<control type="group">
				<height>350</height>
				<visible>Integer.IsGreater(Container($PARAM[id]).NumItems,0) | Container($PARAM[id]).IsUpdating | $PARAM[tambien]</visible>
				<control type="label">
					<left>110</left><top>0</top><width>1200</width><height>44</height>
					<font>vidrio_row</font>
					<textcolor>F2FFFFFF</textcolor>
					<label>$PARAM[titulo]</label>
				</control>
				<control type="list" id="$PARAM[id]">
					<left>90</left><top>40</top><width>1830</width><height>310</height>
					<orientation>horizontal</orientation>
					<scrolltime tween="cubic" easing="out">300</scrolltime>
					<preloaditems>2</preloaditems>
					<onup condition="$PARAM[arriba_si]">$PARAM[arriba]</onup>
					<onup condition="!$PARAM[arriba_si]">$PARAM[arriba_no]</onup>
					<ondown>$PARAM[abajo]</ondown>
					<onback>SetFocus(9001)</onback>
					<onclick condition="String.IsEqual(ListItem.Property(vidrio.tipo),serie)">SetProperty(Vidrio.SerieQ,$INFO[ListItem.Property(vidrio.carpeta_q)],home)</onclick>
					<onclick condition="String.IsEqual(ListItem.Property(vidrio.tipo),serie)">ActivateWindow(1150)</onclick>
					<onclick condition="String.IsEqual(ListItem.Property(vidrio.continuar),1)">PlayMedia($ESCINFO[ListItem.FileNameAndPath])</onclick>
					<onclick condition="!String.IsEqual(ListItem.Property(vidrio.tipo),serie) + !String.IsEqual(ListItem.Property(vidrio.continuar),1)">Action(Info)</onclick>
					<itemlayout width="410" height="300">
						<control type="image">
							<left>20</left><top>22</top><width>370</width><height>208</height>
							<aspectratio>scale</aspectratio>
							<texture background="true" diffuse="vidrio/mask_card.png" fallback="vidrio/white.png">$INFO[ListItem.Art(fanart)]</texture>
						</control>
						<control type="progress">
							<left>40</left><top>208</top><width>330</width><height>8</height>
							<texturebg border="4" colordiffuse="59FFFFFF">vidrio/pill_focus.png</texturebg>
							<lefttexture/><righttexture/>
							<midtexture border="4">vidrio/pill_focus.png</midtexture>
							<info>ListItem.PercentPlayed</info>
							<visible>String.IsEqual(ListItem.Property(vidrio.continuar),1)</visible>
						</control>
					</itemlayout>
					<focusedlayout width="410" height="300">
						<control type="group">
							<animation effect="zoom" start="100" end="110" center="205,126" time="220" tween="cubic" easing="out" reversible="false" condition="Control.HasFocus($PARAM[id])">Conditional</animation>
							<control type="image">
								<left>20</left><top>22</top><width>370</width><height>208</height>
								<aspectratio>scale</aspectratio>
								<texture background="true" diffuse="vidrio/mask_card.png" fallback="vidrio/white.png">$INFO[ListItem.Art(fanart)]</texture>
							</control>
							<control type="image">
								<left>20</left><top>22</top><width>370</width><height>208</height>
								<texture>vidrio/card_focus.png</texture>
								<visible>Control.HasFocus($PARAM[id])</visible>
							</control>
							<control type="progress">
								<left>40</left><top>208</top><width>330</width><height>8</height>
								<texturebg border="4" colordiffuse="59FFFFFF">vidrio/pill_focus.png</texturebg>
								<lefttexture/><righttexture/>
								<midtexture border="4">vidrio/pill_focus.png</midtexture>
								<info>ListItem.PercentPlayed</info>
								<visible>String.IsEqual(ListItem.Property(vidrio.continuar),1)</visible>
							</control>
						</control>
						<control type="label">
							<left>20</left><top>246</top><width>370</width><height>40</height>
							<font>vidrio_small</font>
							<textcolor>FFFFFFFF</textcolor>
							<scroll>true</scroll>
							<label>$INFO[ListItem.Label]</label>
							<visible>Control.HasFocus($PARAM[id])</visible>
						</control>
					</focusedlayout>
					<content target="videos">$PARAM[ruta]</content>
				</control>
			</control>
		</definition>
	</include>
</includes>
'''
open(sys.argv[1], 'w', encoding='utf-8').write(xml)
print('ok')
