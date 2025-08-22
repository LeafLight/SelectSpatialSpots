#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import base64, io
import pandas as pd
from PIL import Image
import plotly.graph_objs as go
from dash import Dash, dcc, html, Input, Output, State, dash_table
import dash

# ------------------ 调色板 ------------------
PALETTES = {
    "Set3": [
        "#8DD3C7","#FFFFB3","#BEBADA","#FB8072","#80B1D3",
        "#FDB462","#B3DE69","#FCCDE5","#D9D9D9","#BC80BD"
    ],
    "Paired": [
        "#A6CEE3","#1F78B4","#B2DF8A","#33A02C","#FB9A99",
        "#E31A1C","#FDBF6F","#FF7F00","#CAB2D6","#6A3D9A"
    ],
    "Tableau10": [
        "#4E79A7","#F28E2B","#E15759","#76B7B2","#59A14F",
        "#EDC948","#B07AA1","#FF9DA7","#9C755F","#BAB0AC"
    ]
}

UNASSIGNED_COLOR = "#A0A0A0"

DEFAULT_GROUPS = 10

def make_groups(palette="Tableau10"):
    return [
        {"Group Name": f"Group {i+1}", "Custom Name": "", "Color": PALETTES[palette][i]}
        for i in range(DEFAULT_GROUPS)
    ]

# ------------------ CSV 解析 ------------------
def parse_csv(contents, has_header=True):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    if has_header:
        df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
    else:
        df = pd.read_csv(io.StringIO(decoded.decode('utf-8')), header=None, names=["Cell_ID","X","Y"])
    cols = {c.lower(): c for c in df.columns}
    need = ["cell_id","x","y"]
    if not all(k in cols for k in need):
        raise ValueError("CSV must contain Cell_ID, X, Y")
    df = df[[cols["cell_id"], cols["x"], cols["y"]]].copy()
    df.columns = ["Cell_ID","X","Y"]
    df["Cell_ID"] = df["Cell_ID"].astype(str)
    return df

# ------------------ 图片解析 ------------------
def decode_image(contents):
    if not contents:
        return None, None, None
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    im = Image.open(io.BytesIO(decoded)).convert("RGBA")
    w, h = im.size
    return contents, w, h

# ------------------ 绘图 ------------------
def build_figure(df, assign_map, point_size,
                 bg_image=None, img_meta=None, img_x_pct=50, img_y_pct=50, img_scale=0.5, img_opacity=0.6):
    if df is None or df.empty:
        fig = go.Figure()
        fig.update_layout(
            xaxis=dict(range=[0,100]), yaxis=dict(range=[0,100], scaleanchor="x"),
            template="plotly_white", dragmode="lasso"
        )
        xr = [0, 100]
        yr = [0, 100]
        dx, dy = xr[1]-xr[0], yr[1]-yr[0]
        xr = [xr[0]-0.05*dx, xr[1]+0.05*dx]
        yr = [yr[0]-0.05*dy, yr[1]+0.05*dy]
        fig.update_layout(
            xaxis=dict(range=xr), yaxis=dict(range=yr, scaleanchor="x"),
            template="plotly_white", dragmode="lasso"
        )

        # 加背景图
        if bg_image and img_meta:
            _, nat_w, nat_h = img_meta
            sizex = (xr[1]-xr[0]) * img_scale
            sizey = sizex * (nat_h/nat_w)
            xpos = xr[0] + (xr[1]-xr[0]) * img_x_pct/100
            ypos = yr[0] + (yr[1]-yr[0]) * img_y_pct/100
            fig.add_layout_image(
                dict(source=bg_image, xref="x", yref="y",
                     x=xpos, y=ypos,
                     sizex=sizex, sizey=sizey,
                     xanchor="center", yanchor="middle",
                     sizing="contain", opacity=img_opacity, layer="below")
            )
        return fig

    colors, hovertext = [], []
    for cid in df["Cell_ID"]:
        if assign_map and cid in assign_map:
            c = assign_map[cid]["Color"]
            g = assign_map[cid]["Group"]
            u = assign_map[cid].get("Custom","")
            colors.append(c)
            hovertext.append(f"Cell: {cid}<br>Group: {g}<br>Custom: {u}")
        else:
            colors.append("#A0A0A0")
            hovertext.append(f"Cell: {cid}<br>Group: ")

    fig = go.Figure(data=[go.Scattergl(
        x=df["X"], y=df["Y"], mode="markers",
        marker=dict(size=point_size, color=colors),
        customdata=df["Cell_ID"], text=hovertext,
        hovertemplate="%{text}<extra></extra>"
    )])
    xr = [df["X"].min(), df["X"].max()]
    yr = [df["Y"].min(), df["Y"].max()]
    dx, dy = xr[1]-xr[0], yr[1]-yr[0]
    xr = [xr[0]-0.05*dx, xr[1]+0.05*dx]
    yr = [yr[0]-0.05*dy, yr[1]+0.05*dy]
    fig.update_layout(
        xaxis=dict(range=xr), yaxis=dict(range=yr, scaleanchor="x"),
        template="plotly_white", dragmode="lasso"
    )

    # 加背景图
    if bg_image and img_meta:
        _, nat_w, nat_h = img_meta
        sizex = (xr[1]-xr[0]) * img_scale
        sizey = sizex * (nat_h/nat_w)
        xpos = xr[0] + (xr[1]-xr[0]) * img_x_pct/100
        ypos = yr[0] + (yr[1]-yr[0]) * img_y_pct/100
        fig.add_layout_image(
            dict(source=bg_image, xref="x", yref="y",
                 x=xpos, y=ypos,
                 sizex=sizex, sizey=sizey,
                 xanchor="center", yanchor="middle",
                 sizing="contain", opacity=img_opacity, layer="below")
        )

    return fig

# ------------------ App 初始化 ------------------
app = Dash(__name__)
app.title = "Spatial Spots Painter"

def palette_options():
    opts = []
    for name, colors in PALETTES.items():
        swatches = html.Div(
            [html.Div(style={"width":"12px","height":"12px","backgroundColor":c,"display":"inline-block","marginRight":"2px"}) for c in colors],
            style={"display":"inline-block","marginLeft":"6px"}
        )
        opts.append({"label": html.Span([html.Span(name), swatches]), "value": name})
    return opts

app.layout = html.Div([
    #html.H3("Select Spatial Spots"),
    html.Img(src=dash.get_asset_url("logo.png"), width="300px"),
    html.Div([
        # 左边栏
        html.Div([
            html.Hr(),
            html.Label("1) Upload Spots CSV", className="side-title"),
            dcc.Upload(id="upload-csv", children=html.Div(["Drag & Drop or ", html.A("Select CSV")]),
                accept=".csv", multiple=False,
                style={"width":"100%","height":"160px","lineHeight":"160px","border":"1px dashed #aaa","textAlign":"center"}),
            dcc.Checklist(id="csv-has-header", options=[{"label":"CSV has header","value":"hdr"}], value=["hdr"]),

            html.Hr(),
            html.Label("2) Palette, Group, Point size", className="side-title"),
            html.Br(),
            html.Label("Palette"),
            dcc.RadioItems(id="palette-choice", options=palette_options(), value="Tableau10"),

            html.Hr(),
            html.Label("Groups Table"),
            dash_table.DataTable(
                id="groups-table",
                columns=[
                    {"name":"Group Name","id":"Group Name","presentation":"input"},
                    {"name":"Custom Name","id":"Custom Name","presentation":"input"},
                    {"name":"Color","id":"Color"}
                ],
                data=make_groups(),
                editable=True, row_selectable="single", style_cell={"textAlign":"center"},
                style_table={"height":"340px","overflowY":"auto"}
            ),

            html.Label("Point Size"),
            dcc.Slider(id="point-size", min=2,max=20,step=1,value=6),

            html.Hr(),
            html.Label("3) Background Image(optional)", className="side-title"),
            dcc.Upload(id="upload-img", children=html.Div(["Drag & Drop or ", html.A("Select Image")]),
                accept="image/*", multiple=False,
                style={"width":"100%","height":"160px","lineHeight":"160px","border":"1px dashed #aaa","textAlign":"center"}),

            html.Hr(),
            html.Button("Export CSV", id="export-btn"),
            dcc.Download(id="download-csv"),
            html.Div(id="status-msg", style={"color":"crimson"})
            ], style={"flex":"0 0 560px","padding":"10px","borderRight":"3px solid #eee"}),

        html.Div([
            dcc.Graph(id="spots-graph", style={"height":"70vh"},
                config={"displaylogo":False,"modeBarButtonsToAdd":["select2d","lasso2d"]}),
            html.Label("Image X (%)"), dcc.Slider(id="img-x", min=0,max=100,step=1,value=50, marks={0:"0%", 25:"25%", 50:"50%", 75:"75%", 100:"100%"}),
            html.Label("Image Y (%)"), dcc.Slider(id="img-y", min=0,max=100,step=1,value=50, marks={0:"0%", 25:"25%", 50:"50%", 75:"75%", 100:"100%"}),
            html.Label("Image Scale"), dcc.Slider(id="img-scale", min=0.05,max=4.0,step=0.01, marks={0.5:"0.5", 1:"1", 2:"2", 4:"4"},value=0.5),
            html.Label("Image Opacity"), dcc.Slider(id="img-opacity", min=0.0,max=1.0,step=0.05,value=0.6),
        ], style={"flex":"1","padding":"10px"})
    ], style={"display":"flex"}),

    dcc.Store(id="df-store"),
    dcc.Store(id="assign-store"),
    dcc.Store(id="img-store"),
    dcc.Store(id="img-meta-store")
])

# ------------------ Callbacks ------------------
@app.callback(
    Output("df-store","data"),
    Output("status-msg","children"),
    Input("upload-csv","contents"),
    State("csv-has-header","value")
)
def handle_csv(contents, header_val):
    if not contents: return None, ""
    try:
        df = parse_csv(contents, "hdr" in (header_val or []))
    except Exception as e:
        return None, f"CSV error: {e}"
    return df.to_dict("records"), ""

@app.callback(
    Output("groups-table","data", allow_duplicate=True),
    Output("assign-store","data", allow_duplicate=True),
    Input("palette-choice","value"),
    State("groups-table","data"),
    State("assign-store","data"),
    prevent_initial_call=True
)
def update_palette(palette, rows, assign_map):
    colors = PALETTES[palette]
    new_rows = []
    for i,row in enumerate(rows):
        new_rows.append({"Group Name": row["Group Name"], "Custom Name": row.get("Custom Name",""), "Color": colors[i]})
    # 更新 assign_map
    if assign_map:
        new_map = {}
        for cid, info in assign_map.items():
            idx = int(info["Group"].split()[-1]) - 1
            new_color = colors[idx % len(colors)]
            new_map[cid] = {"Group": info["Group"], "Custom": info.get("Custom",""), "Color": new_color}
        assign_map = new_map
    return new_rows, assign_map

@app.callback(
    Output("img-store","data"),
    Output("img-meta-store","data"),
    Input("upload-img","contents")
)
def handle_image(contents):
    if not contents: return None, None
    return decode_image(contents)[0], decode_image(contents)

@app.callback(
    Output("spots-graph","figure"),
    Input("df-store","data"),
    Input("assign-store","data"),
    Input("point-size","value"),
    Input("img-store","data"),
    Input("img-meta-store","data"),
    Input("img-x","value"),
    Input("img-y","value"),
    Input("img-scale","value"),
    Input("img-opacity","value")
)
def update_plot(dfrec, assign_map, point_size, bg_img, img_meta, img_x, img_y, img_scale, img_opacity):
    if dfrec is None:
        return build_figure(None, {}, point_size, bg_img, img_meta, img_x, img_y, img_scale, img_opacity)
    return build_figure(pd.DataFrame(dfrec), assign_map or {}, point_size, bg_img, img_meta, img_x, img_y, img_scale, img_opacity)

@app.callback(
    Output("assign-store","data", allow_duplicate=True),
    Input("spots-graph","selectedData"),
    State("groups-table","selected_rows"),
    State("groups-table","data"),
    State("assign-store","data"),
    prevent_initial_call=True
)
def assign_groups(selected, sel_rows, rows, assign_map):
    if not selected or not sel_rows: return assign_map
    idx = sel_rows[0]
    group = rows[idx]["Group Name"]
    custom = rows[idx]["Custom Name"]
    color = rows[idx]["Color"]
    assign_map = assign_map or {}
    for pt in selected["points"]:
        cid = pt["customdata"]
        assign_map[str(cid)] = {"Group": group, "Custom": custom, "Color": color}
    return assign_map

@app.callback(
    Output("download-csv","data"),
    Input("export-btn","n_clicks"),
    State("assign-store","data"),
    State("df-store","data"),
    State("groups-table","data"),
    prevent_initial_call=True
)
def export_csv(_, assign_map, dfrec, groups_data):
    if not dfrec:
        return None

    df = pd.DataFrame(dfrec)
    groups, colors, custom_names = [], [], []

    # 建立 Group -> Custom Name 的映射
    group_to_custom = {row["Group Name"]: row.get("Custom Name", "") for row in groups_data}

    for cid in df["Cell_ID"]:
        cid = str(cid)
        if assign_map and cid in assign_map:
            g = assign_map[cid]["Group"]          # 原始组名 (Group 1, Group 2...)
            c = assign_map[cid]["Color"]
            groups.append(g)
            colors.append(c)
            # 映射 Custom Name，没有就空字符串
            custom_names.append(group_to_custom.get(g, ""))
        else:
            groups.append("")
            colors.append(UNASSIGNED_COLOR)
            custom_names.append("")

    out = pd.DataFrame({
        "Cell_ID": df["Cell_ID"],
        "Group": groups,
        "Custom Name": custom_names,   # 👈 新列
        "Color": colors
    })
    return dcc.send_data_frame(out.to_csv, "spots_assignments.csv", index=False)

@app.callback(
    Output("groups-table","style_data_conditional"),
    Input("groups-table","data")
)
def update_color_preview(rows):
    conds = []
    for i, r in enumerate(rows):
        conds.append({
            "if": {"row_index": i, "column_id": "Color"},
            "backgroundColor": r["Color"],
            "color": r["Color"]
        })
    return conds

if __name__ == "__main__":
    app.run(debug=True)

