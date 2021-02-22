import argparse
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash_extensions import Keyboard
import time

import flask
import glob
import os
import re

def build_app(derivatives_path):

    static_image_route = "/images/"
    image_directory = os.getcwd()
    preproc_steps_template = {
        "sdc": "Susceptibility distortion correction",
        "bbregister": "Alignment of functional and anatomical MRI data",
        "carpetplot": "BOLD Summary",
        "confoundcorr": "Correlations among nuisance regressors",
        "rois": "Brain mask and (temporal/anatomical) CompCor ROIs",
    }
    default_preproc_step = "carpetplot"
    idx_fname = 0

    def list_runs(subject):
        paths = sorted(
            [
                os.path.basename(p)
                for p in glob.glob(
                    f"{derivatives_path}/sub-{subject}/figures/*desc-{default_preproc_step}_bold.svg"
                )
            ]
        )
        runs = [
            "_".join(
                [
                    ent
                    for ent in p.split("_")
                    if ent.split("-")[0] in ["ses", "task", "run"]
                ]
            )
            for p in paths
        ]
        return runs, paths

    def check_preproc_steps(subject, run):
        svgs = sorted(
            [
                os.path.basename(p)
                for p in glob.glob(
                    f"{derivatives_path}/sub-{subject}/figures/sub-{subject}_{run}_desc-*_bold.svg"
                )
            ]
        )

        preproc_steps_names = [
                re.match(".*?desc-(.*?)_bold.svg", svg)[1]
                for svg in svgs
            ]

        return preproc_steps_names

    subjects = sorted(
        [
            os.path.basename(p[:-1]).split("-")[1]
            for p in glob.glob(f"{derivatives_path}/sub-*/")
        ]
    )
    default_runs = [
        {"label": run, "value": path} for run, path in zip(*list_runs(subjects[0]))
    ]

    
    preproc_steps_found = check_preproc_steps(subjects[0], default_runs[0]["label"])
    preproc_steps = [
        (preproc_steps_template[preproc_step_found], preproc_step_found)
        for preproc_step_found in preproc_steps_found
        if preproc_step_found in list(preproc_steps_template.keys())

    ]

    app = dash.Dash()

    app.layout = html.Div(
        [
            Keyboard(id="keyboard"),
            dcc.Store(id='fname-idx', data=0),
            dcc.Store(id='left_press', data=False),
            dcc.Store(id='right_press', data=False),
            dcc.Dropdown(
                id="subject-dropdown",
                options=[
                    {"label": f"sub-{subject}", "value": subject}
                    for subject in subjects
                ],
                value=subjects[0],
            ),
            dcc.Dropdown(
                id="run-dropdown", options=default_runs, value=default_runs[0]["value"]
            ),
            dcc.Tabs(
                id="step-tabs",
                children=[
                    dcc.Tab(label=step_name, value=step)
                    for step_name, step in preproc_steps
                ],
                value=preproc_steps[0][1],
            ),
            html.ObjectEl(id="image", style={'width': "100%"}),
        ]
    ) 

    @app.callback(
        dash.dependencies.Output("run-dropdown", "options"),
        [dash.dependencies.Input("subject-dropdown", "value")],
    )
    def update_runs_list(subject):
        return [{"label": run, "value": path} for run, path in zip(*list_runs(subject))]

    @app.callback(
        dash.dependencies.Output('left_press', 'data'),
        [
            dash.dependencies.Input("keyboard", "keydown"),
            dash.dependencies.Input("keyboard", "n_keydowns"),
        ],
        dash.dependencies.State('left_press', 'data'),
    )
    def update_left(key_status, n_press, data):
        if key_status:
            if (key_status["key"] == "ArrowLeft"):
                return True
        return False

    @app.callback(
        dash.dependencies.Output('right_press', 'data'),
        [
            dash.dependencies.Input("keyboard", "keydown"),
            dash.dependencies.Input("keyboard", "n_keydowns"),
        ],
        dash.dependencies.State('right_press', 'data'),
    )
    def update_right(key_status, n_press, data):
        if key_status:
            if (key_status["key"] == "ArrowRight"):
                return True
        return False

    @app.callback(
        dash.dependencies.Output("fname-idx", "data"),
        [
            dash.dependencies.Input("run-dropdown", "value"),
            dash.dependencies.Input("run-dropdown", "options"),
            dash.dependencies.Input("keyboard", "n_keydowns"),
        ],
        [
            dash.dependencies.State("fname-idx", "data"),
            dash.dependencies.State('left_press', 'data'),
            dash.dependencies.State('right_press', 'data'),
        ]
    )
    def update_fname_idx(fname, fnames, n_press, fname_idx, left_press, right_press):
        for ii, curr_fname in enumerate(fnames):
            if curr_fname["value"] == fname:
                fname_idx = ii
        if right_press:
            if fname_idx < (len(fnames) - 1):
                fname_idx = fname_idx + 1
        elif left_press:
            if fname_idx > 0:
                fname_idx = fname_idx - 1
                    
        return fname_idx

    @app.callback(
        dash.dependencies.Output("run-dropdown", "value"),
        [
            dash.dependencies.Input("subject-dropdown", "value"),
            dash.dependencies.Input("run-dropdown", "options"),
            dash.dependencies.Input("keyboard", "n_keydowns"),
        ],
        [
            dash.dependencies.State("fname-idx", "data"),
            dash.dependencies.State('left_press', 'data'),
            dash.dependencies.State('right_press', 'data'),
        ]
    )
    def update_run_value(subject, fnames, n_press, fname_idx, left_press, right_press):
        if left_press | right_press:
            return list_runs(subject)[1][fname_idx]
        return list_runs(subject)[1][0]

    @app.callback(
        dash.dependencies.Output("image", "data"),
        [
            dash.dependencies.Input("subject-dropdown", "value"),
            dash.dependencies.Input("run-dropdown", "value"),
            dash.dependencies.Input("step-tabs", "value"),
        ],
    )
    def update_image_src(subject, fname, step):
        if fname:
            return os.path.join(
                    static_image_route, subject, fname.replace(f"-{default_preproc_step}_", "-{}_".format(step))
                )

    @app.server.route("/images/<subject>/<image_path>")
    def serve_image(subject, image_path):
        image_directory = os.path.abspath(
            os.path.join(derivatives_path, "sub-%s" % subject, "figures")
        )
        if not os.path.exists(os.path.join(image_directory, image_path)):
            raise RuntimeError("image_path not found")
        return flask.send_from_directory(image_directory, image_path)

    return app


def parse_args():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter,
        description="run dash app to view fmriprep qc images",
    )
    parser.add_argument("derivatives_path", help="fmriprep derivative folder")
    parser.add_argument("--port", action="store", default=8050, help="server port")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    app = build_app(args.derivatives_path)
    app.run_server(debug=True, dev_tools_silence_routes_logging=False, port=args.port)
