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
        "bbregister": "Alignment of functional and anatomical MRI data (freesurfer)",
        "flirtbbr": "Alignment of functional and anatomical MRI data (flirt)",
        "carpetplot": "BOLD Summary",
        "confoundcorr": "Correlations among nuisance regressors",
        "rois": "Brain mask and (temporal/anatomical) CompCor ROIs",
        "aroma": "ICA-AROMA denoising"
    }
    anat_template = {
        "MNI152NLin6Asym": "Spatial normalization of anatomical MRI to MNI152NLin6Asym.",
        "MNI152NLin2009cAsym": "Spatial normalization of anatomical MRI to MNI152NLin2009cAsym.",
        "dseg": "Anatomical brain mask and brain tissue segmentation"
    }
    default_preproc_step = "carpetplot"

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

    def check_anat(subject):
        svgs = sorted(
            [
                os.path.basename(p)
                for p in glob.glob(
                    f"{derivatives_path}/sub-{subject}/figures/sub-{subject}_space-*_T1w.svg"
                )
            ]
        )

        anat_names = [
                re.match(".*?_space-(.*?)_T1w.svg", svg)[1]
                for svg in svgs
            ]
        seg_file = f"{derivatives_path}/sub-{subject}/figures/sub-{subject}_dseg.svg"
        if os.path.exists(seg_file):
            anat_names = anat_names + ["dseg"]

        return anat_names

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
    anat_founds = check_anat(subjects[0])
    anat_steps = [
        (anat_template[anat_found], anat_found)
        for anat_found in anat_founds
        if anat_found in list(anat_template.keys())
    ] 

    steps_tab = preproc_steps + anat_steps

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
                    for step_name, step in steps_tab
                ],
                value=preproc_steps[0][1],
            ),
            html.Img(id="image", style={'width': "100%"}),
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
        dash.dependencies.Output("image", "src"),
        [
            dash.dependencies.Input("subject-dropdown", "value"),
            dash.dependencies.Input("run-dropdown", "value"),
            dash.dependencies.Input("step-tabs", "value"),
        ],
    )
    def update_image_src(subject, fname, step):
        print(fname)
        if fname:
            # if selected tab is functionnal data
            if step in preproc_steps_template.keys():
                return os.path.join(
                        static_image_route, subject, fname.replace(f"-{default_preproc_step}_", "-{}_".format(step)))
            # else if selected tab is anatomical
            elif step in anat_template.keys():
                subject_files = os.path.join(
                    derivatives_path, f"sub-{subject}", "figures", f"sub-{subject}_*.svg")
                for filepath in glob.glob(subject_files):
                    if step in filepath:
                        image_file = filepath.split("/")[-1]
                        return os.path.join(static_image_route, subject, image_file)
            else:
                raise RuntimeError("tab does not exists")

    @app.server.route(f"{static_image_route}<subject>/<image_file>")
    def serve_image(subject, image_file):
        image_directory = os.path.abspath(
            os.path.join(derivatives_path, "sub-%s" % subject, "figures")
        )
        if not os.path.exists(os.path.join(image_directory, image_file)):
            raise RuntimeError("image_path not found")
        return flask.send_from_directory(image_directory, image_file)

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
