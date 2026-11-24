"""Genera xml/Includes_Vidrio.xml (variables repetidas por fila)."""
import sys
FILAS = range(5100, 5109)  # 5100 = Continuar viendo (Trakt)
EN_VIVO = {'VidrioFanart': '$INFO[Container(5120).ListItem.Art(fanart)]',
           'VidrioTitulo': '$INFO[Container(5120).ListItem.Label]',
           'VidrioMeta': '$INFO[Container(5120).ListItem.Property(vidrio.meta)]',
           'VidrioSinopsis': '$INFO[Container(5120).ListItem.Plot]',
           'VidrioKicker': '$INFO[Container(5120).ListItem.Property(vidrio.etiqueta)]'}

def var(nombre, plantilla, defecto=None):
    out = [f'\t<variable name="{nombre}">']
    if nombre in EN_VIVO:  # filas de partidos (5120 en vivo, 5121 próximos): sin las variables de tráiler
        for fila in (5120, 5121):
            out.append(f'\t\t<value condition="Control.HasFocus({fila})">{EN_VIVO[nombre].replace("5120", str(fila))}</value>')
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
    if nombre == 'VidrioAccion':
        out.append('\t\t<value condition="Control.HasFocus(5120) + System.Platform.Android">Ver en DGO</value>')
        out.append('\t\t<value condition="Control.HasFocus(5120)">Abrir DGO</value>')
        out.append('\t\t<value condition="Control.HasFocus(5121) + String.IsEqual(Container(5121).ListItem.Property(vidrio.recordado),1)">No avisar</value>')
        out.append('\t\t<value condition="Control.HasFocus(5121)">Avisarme</value>')
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

	<!-- Partidos (plugin ?lista=envivo y ?lista=proximos). "Deportes en vivo" (5120) va arriba de todo y solo se ve con
	     algún partido en juego; elegir uno abre su canal en DGO (Android) o la página de DGO en la App Store (tvOS),
	     como la guía. "Próximos partidos" (5121) va debajo de "Continuar viendo"; elegir uno pone (o saca) un aviso
	     5 minutos antes (plugin ?recordar=), y la pastilla pasa a celeste. Los de los equipos favoritos van primero,
	     con "★" en la pastilla (dorada si no tienen aviso).
	     Las listas 5098 y 5097 de Home.xml, fuera de pantalla, las cargan aunque estén ocultas. -->
	<include name="VidrioTarjetaPartido">
		<control type="image">
			<left>20</left><top>22</top><width>370</width><height>208</height>
			<texture diffuse="vidrio/mask_card.png" colordiffuse="FF1C2230">vidrio/white.png</texture>
		</control>
		<control type="image">
			<left>36</left><top>36</top><width>150</width><height>32</height>
			<texture border="4" colordiffuse="FFE53935">vidrio/pill_focus.png</texture>
			<visible>String.IsEqual(ListItem.Property(vidrio.vivo),1)</visible>
		</control>
		<control type="image">
			<left>36</left><top>36</top><width>150</width><height>32</height>
			<texture border="4" colordiffuse="40FFFFFF">vidrio/pill_focus.png</texture>
			<visible>!String.IsEqual(ListItem.Property(vidrio.vivo),1) + !String.IsEqual(ListItem.Property(vidrio.recordado),1) + !String.IsEqual(ListItem.Property(vidrio.favorito),1)</visible>
		</control>
		<control type="image">
			<left>36</left><top>36</top><width>150</width><height>32</height>
			<texture border="4" colordiffuse="FFD4A017">vidrio/pill_focus.png</texture>
			<visible>!String.IsEqual(ListItem.Property(vidrio.vivo),1) + !String.IsEqual(ListItem.Property(vidrio.recordado),1) + String.IsEqual(ListItem.Property(vidrio.favorito),1)</visible>
		</control>
		<control type="image">
			<left>36</left><top>36</top><width>150</width><height>32</height>
			<texture border="4" colordiffuse="FF2E86DE">vidrio/pill_focus.png</texture>
			<visible>String.IsEqual(ListItem.Property(vidrio.recordado),1)</visible>
		</control>
		<control type="label">
			<left>36</left><top>36</top><width>150</width><height>32</height>
			<align>center</align><aligny>center</aligny>
			<font>vidrio_small</font><textcolor>FFFFFFFF</textcolor>
			<label>$INFO[ListItem.Property(vidrio.pastilla)]</label>
			<visible>!String.IsEqual(ListItem.Property(vidrio.recordado),1)</visible>
		</control>
		<control type="label">
			<left>36</left><top>36</top><width>150</width><height>32</height>
			<align>center</align><aligny>center</aligny>
			<font>vidrio_small</font><textcolor>FFFFFFFF</textcolor>
			<label>$INFO[ListItem.Property(vidrio.pastilla)]</label>
			<visible>String.IsEqual(ListItem.Property(vidrio.recordado),1)</visible>
		</control>
		<control type="image">
			<left>264</left><top>30</top><width>110</width><height>44</height>
			<aspectratio align="right">keep</aspectratio>
			<texture background="true">$INFO[ListItem.Art(logo)]</texture>
		</control>
		<control type="image">
			<left>40</left><top>84</top><width>96</width><height>96</height>
			<aspectratio>keep</aspectratio>
			<texture background="true">$INFO[ListItem.Art(local)]</texture>
		</control>
		<control type="image">
			<left>274</left><top>84</top><width>96</width><height>96</height>
			<aspectratio>keep</aspectratio>
			<texture background="true">$INFO[ListItem.Art(visitante)]</texture>
		</control>
		<control type="label">
			<left>130</left><top>92</top><width>150</width><height>64</height>
			<align>center</align><aligny>center</aligny>
			<font>vidrio_marcador</font><textcolor>FFFFFFFF</textcolor>
			<label>$INFO[ListItem.Property(vidrio.marcador)]</label>
		</control>
		<control type="label">
			<left>130</left><top>156</top><width>150</width><height>30</height>
			<align>center</align><aligny>center</aligny>
			<font>vidrio_small</font><textcolor>CCFFFFFF</textcolor>
			<label>$INFO[ListItem.Property(vidrio.estado)]</label>
		</control>
		<control type="label">
			<left>36</left><top>190</top><width>338</width><height>32</height>
			<align>center</align><aligny>center</aligny>
			<font>vidrio_small</font><textcolor>B3FFFFFF</textcolor>
			<label>$INFO[ListItem.Property(vidrio.competencia)]</label>
		</control>
	</include>

	<include name="VidrioFilaPartidos">
		<param name="id"/><param name="titulo"/><param name="cargador"/><param name="lista"/>
		<param name="arriba"/><param name="abajo"/>
		<definition>
			<control type="group">
				<height>350</height>
				<visible>Integer.IsGreater(Container($PARAM[cargador]).NumItems,0)</visible>
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
					<onup>$PARAM[arriba]</onup>
					<ondown>$PARAM[abajo]</ondown>
					<onback>SetFocus(9001)</onback>
					<onclick condition="!String.IsEqual(ListItem.Property(vidrio.vivo),1)">RunPlugin(plugin://plugin.video.vidrio/?recordar=$INFO[ListItem.Property(vidrio.partido_id)])</onclick>
					<onclick condition="String.IsEqual(ListItem.Property(vidrio.vivo),1) + System.Platform.Android + !String.IsEmpty(ListItem.Property(vidrio.dgo))">StartAndroidActivity(com.directv.dtvlatam,android.intent.action.VIEW,,dtvmobile://dgo/$INFO[ListItem.Property(vidrio.dgo)]?reopened=true,268468224,,,,com.directvgo.presentation.tv.splash.router.SplashRouterActivity)</onclick>
					<onclick condition="String.IsEqual(ListItem.Property(vidrio.vivo),1) + System.Platform.Android + String.IsEmpty(ListItem.Property(vidrio.dgo))">StartAndroidActivity(com.directv.dtvlatam,android.intent.action.VIEW,,dtvmobile://dgo/home/live?reopened=true,268468224,,,,com.directvgo.presentation.tv.splash.router.SplashRouterActivity)</onclick>
					<onclick condition="String.IsEqual(ListItem.Property(vidrio.vivo),1) + !System.Platform.Android">RunPlugin(plugin://plugin.video.vidrio/?abrir=itms-apps%3A%2F%2Fapps.apple.com%2Far%2Fapp%2Fid1349939060)</onclick>
					<itemlayout width="410" height="300">
						<include>VidrioTarjetaPartido</include>
						<control type="label">
							<left>20</left><top>246</top><width>370</width><height>40</height>
							<font>vidrio_small</font><textcolor>B3FFFFFF</textcolor>
							<label>$INFO[ListItem.Label2]</label>
						</control>
					</itemlayout>
					<focusedlayout width="410" height="300">
						<control type="group">
							<animation effect="zoom" start="100" end="110" center="205,126" time="220" tween="cubic" easing="out" reversible="false" condition="Control.HasFocus($PARAM[id])">Conditional</animation>
							<include>VidrioTarjetaPartido</include>
							<control type="image">
								<left>20</left><top>22</top><width>370</width><height>208</height>
								<texture>vidrio/card_focus.png</texture>
								<visible>Control.HasFocus($PARAM[id])</visible>
							</control>
						</control>
						<control type="label">
							<left>20</left><top>246</top><width>370</width><height>40</height>
							<font>vidrio_small</font><textcolor>FFFFFFFF</textcolor>
							<scroll>true</scroll>
							<label>$INFO[ListItem.Label2]</label>
						</control>
					</focusedlayout>
					<content target="videos">plugin://plugin.video.vidrio/?lista=$PARAM[lista]&amp;v=$INFO[Window(home).Property(Vidrio.EnVivo)]</content>
				</control>
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
