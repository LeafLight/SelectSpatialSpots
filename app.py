import base64
import io
from PIL import Image
import pandas as pd
from dash import Dash, dcc, html, Input, Output, State, dash_table
import plotly.graph_objs as go

app = Dash(__name__)
app.title = "Spatial Spots Painter"

# ---------- Helpers ----------
DEFAULT_GROUP_ROWS = 10
UNASSIGNED_COLOR = "#A0A0A0"

COLOR_OPTIONS = [
    {"label": "Red", "value": "#FF0000"},
    {"label": "Green", "value": "#00FF00"},
    {"label": "Blue", "value": "#0000FF"},
    {"label": "Yellow", "value": "#FFFF00"},
    {"label": "Orange", "value": "#FFA500"},
    {"label": "Purple", "value": "#800080"},
    {"label": "Pink", "value": "#FFC0CB"},
    {"label": "Brown", "value": "#8B4513"},
    {"label": "Gray", "value": "#808080"},
    {"label": "Black", "value": "#000000"},
]

def make_empty_groups(n=DEFAULT_GROUP_ROWS):
    return [{"Color":"", "Group Name":"", "Active": "No"} for _ in range(n)]

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
        raise ValueError("CSV must contain columns: Cell_ID, X, Y")
    df = df[[cols["cell_id"], cols["x"], cols["y"]]].copy()
    df.columns = ["Cell_ID","X","Y"]

    # ensure serializable
    df["Cell_ID"] = df["Cell_ID"].astype(str)
    df["X"] = df["X"].astype(float)
    df["Y"] = df["Y"].astype(float)
    return df

def decode_image(contents):
    if not contents:
        return None, None, None
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    im = Image.open(io.BytesIO(decoded)).convert("RGBA")
    w, h = im.size
    return contents, w, h

def build_figure(df, assign_map, point_size, bg_image, img_meta,
                 img_x, img_y, img_scale, img_opacity):
    if df is None or df.empty:
        fig = go.Figure()
        xr = [0, 100]
        yr = [0, 100]
        fig.update_layout(
            xaxis=dict(range=xr, visible=True),
            yaxis=dict(range=yr, visible=True, scaleanchor="x", scaleratio=1),
            margin=dict(l=20, r=20, t=30, b=20),
            dragmode="lasso",
            template="plotly_white"
        )
    else:
        # colors
        colors, hovertext = [], []
        for cid in df["Cell_ID"]:
            if assign_map and cid in assign_map:
                colors.append(assign_map[cid].get("Color") or UNASSIGNED_COLOR)
                hovertext.append(f"Cell_ID: {cid}<br>Group: {assign_map[cid].get('Group','')}")
            else:
                colors.append(UNASSIGNED_COLOR)
                hovertext.append(f"Cell_ID: {cid}<br>Group: ")
        fig = go.Figure(
            data=[
                go.Scattergl(
                    x=df["X"], y=df["Y"],
                    mode="markers",
                    marker=dict(size=point_size, color=colors, line=dict(width=0)),
                    customdata=df["Cell_ID"],
                    hovertemplate="%{text}<extra></extra>",
                    text=hovertext
                )
            ]
        )
        xr = [df["X"].min(), df["X"].max()]
        yr = [df["Y"].min(), df["Y"].max()]
        dx = xr[1]-xr[0] or 1
        dy = yr[1]-yr[0] or 1
        pad = 0.05
        xr = [xr[0]-dx*pad, xr[1]+dx*pad]
        yr = [yr[0]-dy*pad, yr[1]+dy*pad]

        fig.update_layout(
            xaxis=dict(range=xr, zeroline=False),
            yaxis=dict(range=yr, scaleanchor="x", scaleratio=1, zeroline=False),
            margin=dict(l=20,r=20,t=30,b=20),
            dragmode="lasso",
            template="plotly_white"
        )

    # --- add background image if exists ---
    if bg_image and img_meta and img_scale:
        _, nat_w, nat_h = img_meta
        xr = fig.layout.xaxis.range
        yr = fig.layout.yaxis.range

        # 将 slider (0-100) 转换为百分比坐标
        xpos = xr[0] + (xr[1]-xr[0]) * (img_x/100.0)
        ypos = yr[0] + (yr[1]-yr[0]) * (img_y/100.0)

        sizex = (xr[1] - xr[0]) * img_scale
        sizey = sizex * (nat_h / nat_w)

        fig.add_layout_image(
            dict(
                source=bg_image,
                xref="x", yref="y",
                x=xpos, y=ypos,
                sizex=sizex, sizey=sizey,
                xanchor="center", yanchor="middle",
                sizing="contain",
                opacity=img_opacity,
                layer="below"
            )
        )
    return fig

# ---------- Layout ----------
app.layout = html.Div([
    html.H3("Spatial Spots Painter"),
    html.Div([
        html.Div([
            html.Label("1) Upload Spots CSV"),
            dcc.Upload(
                id="upload-csv",
                children=html.Div(["Drag & Drop or ", html.A("Select CSV")]),
                accept=".csv",
                multiple=False,
                style={"width":"100%","height":"60px","lineHeight":"60px",
                       "borderWidth":"1px","borderStyle":"dashed",
                       "borderRadius":"8px","textAlign":"center","margin-bottom":"8px"}
            ),
            dcc.Checklist(
                id="csv-has-header",
                options=[{"label":"CSV has header row", "value":"hdr"}],
                value=["hdr"],
                style={"margin-bottom":"10px"}
            ),

            html.Label("2) Groups Palette"),
            dash_table.DataTable(
                id="groups-table",
                columns=[
                    {"name": "Color", "id": "Color", "presentation": "dropdown"},
                    {"name": "Group Name", "id": "Group Name", "presentation": "input"},
                    {"name": "Active", "id": "Active", "presentation": "dropdown"}
                ],
                data=make_empty_groups(),
                editable=True,
                row_deletable=True,
                dropdown={
                    "Color": {"options": COLOR_OPTIONS},
                    "Active": {"options": [{"label":"Yes","value":"Yes"},
                                           {"label":"No","value":"No"}]}
                },
                style_table={"height":"360px","overflowY":"auto","border":"1px solid #ddd"},
                style_cell={"fontSize":"13px","padding":"6px"},
                style_header={"backgroundColor":"#f7f7f7","fontWeight":"600"},
                persistence=True, persistence_type="session"
            ),
            html.Button("Add Row", id="add-row", n_clicks=0,
                        style={"width":"100%","margin":"6px 0 12px"}),

            html.Label("Point Size"),
            dcc.Slider(id="point-size", min=2, max=20, step=1, value=6,
                       tooltip={"placement":"bottom"}),
            html.Hr(),

            html.Label("3) Background Image (optional)"),
            dcc.Upload(
                id="upload-img",
                children=html.Div(["Drag & Drop or ", html.A("Select Image")]),
                accept="image/*",
                multiple=False,
                style={"width":"100%","height":"60px","lineHeight":"60px",
                       "borderWidth":"1px","borderStyle":"dashed",
                       "borderRadius":"8px","textAlign":"center","margin-bottom":"8px"}
            ),
            html.Div([
                html.Label("Image X (%)"),
                dcc.Slider(id="img-x", min=0, max=100, step=0.1, value=50),
                html.Label("Image Y (%)"),
                dcc.Slider(id="img-y", min=0, max=100, step=0.1, value=50),
                html.Label("Image Scale"),
                dcc.Slider(id="img-scale", min=0.05, max=2.0, step=0.01, value=0.5),
                html.Label("Image Opacity"),
                dcc.Slider(id="img-opacity", min=0.0, max=1.0, step=0.05, value=0.6)
            ]),
            html.Div(id="status-msg", style={"color":"crimson","minHeight":"20px"}),

            html.Hr(),
            html.Button("Export CSV (Cell_ID, Group, Color)",
                        id="export-btn", n_clicks=0,
                        style={"width":"100%","margin":"6px 0"}),
            dcc.Download(id="download-csv"),
        ], style={"flex":"0 0 320px","padding":"10px",
                  "borderRight":"1px solid #eee"}),

        html.Div([
            html.Div("Tip: choose an Active row (Yes), then use lasso/box to paint spots.",
                     style={"fontSize":"12px","color":"#555"}),
            dcc.Graph(id="spots-graph", style={"height":"78vh"},
                      config={"displaylogo": False,
                              "modeBarButtonsToAdd": ["select2d","lasso2d"]})
        ], style={"flex":"1","padding":"10px"})
    ], style={"display":"flex","gap":"12px"}),

    dcc.Store(id="df-store"),
    dcc.Store(id="assign-store"),
    dcc.Store(id="img-store"),
    dcc.Store(id="img-meta-store")
])

# ---------- Callbacks ----------
@app.callback(
    Output("groups-table","data"),
    Input("add-row","n_clicks"),
    State("groups-table","data"),
    prevent_initial_call=True
)
def add_group_row(n, rows):
    rows = rows or []
    rows.append({"Color":"", "Group Name":"", "Active": "No"})
    return [dict(r) for r in rows]

@app.callback(
    Output("df-store","data"),
    Output("status-msg","children"),
    Input("upload-csv","contents"),
    State("csv-has-header","value")
)
def handle_csv(contents, header_val):
    if not contents:
        return None, ""
    has_header = "hdr" in (header_val or [])
    try:
        df = parse_csv(contents, has_header=has_header)
    except Exception as e:
        return None, f"CSV error: {e}"
    return df.to_dict("records"), ""

@app.callback(
    Output("groups-table","data", allow_duplicate=True),
    Input("groups-table","data_timestamp"),
    State("groups-table","data"),
    prevent_initial_call=True
)
def enforce_single_active(_ts, rows):
    if not rows:
        return rows
    active_idxs = [i for i,r in enumerate(rows) if r.get("Active") == "Yes"]
    if len(active_idxs) <= 1:
        return [dict(r) for r in rows]
    keep = active_idxs[-1]
    for i in range(len(rows)):
        rows[i]["Active"] = "Yes" if i == keep else "No"
    return [dict(r) for r in rows]

@app.callback(
    Output("img-store","data"),
    Output("img-meta-store","data"),
    Input("upload-img","contents")
)
def handle_image(contents):
    if not contents:
        return None, None
    img_data, w, h = decode_image(contents)
    return img_data, (img_data, w, h)

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
def update_plot(dfrec, assign_map, point_size,
                bg_img, img_meta, img_x, img_y,
                img_scale, img_opacity):
    if dfrec is None:
        return build_figure(None, {}, point_size,
                            bg_img, img_meta,
                            img_x, img_y, img_scale, img_opacity)
    df = pd.DataFrame(dfrec)
    assign_map = assign_map or {}
    return build_figure(df, assign_map, point_size,
                        bg_img, img_meta,
                        img_x, img_y, img_scale, img_opacity)

@app.callback(
    Output("assign-store","data", allow_duplicate=True),
    Input("spots-graph","selectedData"),
    State("groups-table","data"),
    State("assign-store","data"),
    State("df-store","data"),
    prevent_initial_call=True
)
def assign_groups(selected, groups, assign_map, dfrec):
    if not selected or not dfrec:
        return assign_map
    df = pd.DataFrame(dfrec)
    assign_map = assign_map or {}
    active = [g for g in groups if g.get("Active") == "Yes"]
    if not active:
        return assign_map
    active = active[0]
    color = active.get("Color") or UNASSIGNED_COLOR
    groupname = active.get("Group Name") or ""
    for pt in selected.get("points", []):
        cid = pt["customdata"]
        assign_map[str(cid)] = {"Group": str(groupname),
                                "Color": str(color)}
    return {str(k): dict(v) for k,v in assign_map.items()}

@app.callback(
    Output("download-csv","data"),
    Input("export-btn","n_clicks"),
    State("assign-store","data"),
    State("df-store","data"),
    prevent_initial_call=True
)
def export_assignments(n, assign_map, dfrec):
    if not dfrec:
        return None
    df = pd.DataFrame(dfrec)
    assign_map = assign_map or {}
    groups, colors = [], []
    for cid in df["Cell_ID"]:
        cid = str(cid)
        if cid in assign_map:
            groups.append(assign_map[cid].get("Group"))
            colors.append(assign_map[cid].get("Color"))
        else:
            groups.append("")
            colors.append(UNASSIGNED_COLOR)
    out = pd.DataFrame({"Cell_ID":df["Cell_ID"],
                        "Group":groups, "Color":colors})
    return dcc.send_data_frame(out.to_csv,
                               "spots_assignments.csv",
                               index=False)

if __name__ == "__main__":
    app.run(debug=True)

