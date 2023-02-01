from math import radians, sin, cos
from PIL import Image, ImageDraw
import asyncio
import typing

if typing.TYPE_CHECKING:
    from . import Skin

def is_not_existing(dic, key1=None, key2=None, key3=None):
    try:
        if key1 is None:
            dic
        if key2 is None:
            dic[key1]
        elif key3 is None:
            dic[key1][key2]
        else:
            dic[key1][key2][key3]
        return False
    except KeyError:
        return True


def append_dict(dic, key1, key2, key3, value):
    if is_not_existing(dic, key1, key2, key3):
        try:
            dic[key1][key2][key3] = value
        except KeyError:
            try:
                dic[key1][key2] = {}
                dic[key1][key2][key3] = value
            except KeyError:
                dic[key1] = {}
                dic[key1][key2] = {}
                dic[key1][key2][key3] = value
    return dic


class Render:
    def __init__(
            self,
            player: "Skin",
            vr: int = 0,
            hr: int = 0,
            hrh: int = 0,
            vrll: int = 0,
            vrrl: int = 0,
            vrla: int = 0,
            vrra: int = 0,
            vrc: int = 30,
            ratio: int = 12,
            head_only: bool = False,
            display_hair: bool = False,
            display_layers: bool = False,
            display_cape: bool = False,
            aa: bool = False,
    ):
        self.vr = vr
        self.hr = hr
        self.hrh = hrh
        self.vrll = vrll
        self.vrrl = vrrl
        self.vrla = vrla
        self.vrra = vrra
        self.vrc = vrc
        self.head_only = head_only
        self.ratio = ratio
        self.display_hair = display_hair
        self.display_cape = display_cape if player.raw_cape else False
        self.layers = display_layers
        self.player = player
        self.aa = aa
        self.rendered_image = None

        self.loop = asyncio.get_event_loop()
        self.cube_points = []
        self.polygons = {}

        self.cos_a = None
        self.sin_a = None
        self.cos_b = None
        self.sin_b = None

        self.min_x = 0
        self.max_x = 0
        self.min_y = 0
        self.max_y = 0

    async def get_render(self):
        skin = self.player.raw_skin
        hd_ratio = int(skin.size[0] / 64)

        def render_skin(skin):
            self.calculate_angles()
            self.determine_faces()
            self.generate_polygons(hd_ratio, skin, self.player.raw_cape)
            self.member_rotation(hd_ratio)
            self.create_project_plan()

            im = self.display_image()
            return im

        im = await self.loop.run_in_executor(
            None,
            render_skin,
            skin
        )

        return im

    def calculate_angles(self):
        self.body_angles = {}
        alpha = radians(self.vr)
        beta = radians(self.hr)

        self.cos_a, self.sin_a = cos(alpha), sin(alpha)
        self.cos_b, self.sin_b = cos(beta), sin(beta)

        self.body_angles["torso"] = (cos(0), sin(0), cos(0), sin(0))
        self.body_angles["torso_layer"] = (cos(0), sin(0), cos(0), sin(0))

        alpha_cape = (-radians(self.vrc))
        self.body_angles["cape"] = (cos(alpha_cape), sin(alpha_cape), cos(0), sin(0))
        #self.body_angles["cape"] = (cos(0), sin(alpha_cape), cos(0), sin(0))

        alpha_head = 0
        beta_head = radians(self.hrh)
        self.body_angles["head"] = (cos(alpha_head), sin(alpha_head), cos(beta_head), sin(beta_head))
        self.body_angles["helmet"] = (cos(alpha_head), sin(alpha_head), cos(beta_head), sin(beta_head))

        alpha_r_arm = radians(self.vrra)
        beta_r_arm = 0
        self.body_angles["r_arm"] = (cos(alpha_r_arm), sin(alpha_r_arm), cos(beta_r_arm), sin(beta_r_arm))
        self.body_angles["r_arm_layer"] = (cos(alpha_r_arm), sin(alpha_r_arm), cos(beta_r_arm), sin(beta_r_arm))

        alpha_l_arm = radians(self.vrla)
        beta_l_arm = 0
        self.body_angles["l_arm"] = (cos(alpha_l_arm), sin(alpha_l_arm), cos(beta_l_arm), sin(beta_l_arm))
        self.body_angles["l_arm_layer"] = (cos(alpha_l_arm), sin(alpha_l_arm), cos(beta_l_arm), sin(beta_l_arm))

        alpha_r_leg = radians(self.vrrl)
        beta_r_leg = 0
        self.body_angles["r_leg"] = (cos(alpha_r_leg), sin(alpha_r_leg), cos(beta_r_leg), sin(beta_r_leg))
        self.body_angles["r_leg_layer"] = (cos(alpha_r_leg), sin(alpha_r_leg), cos(beta_r_leg), sin(beta_r_leg))

        alpha_l_leg = radians(self.vrll)
        beta_l_leg = 0
        self.body_angles["l_leg"] = (cos(alpha_l_leg), sin(alpha_l_leg), cos(beta_l_leg), sin(beta_l_leg))
        self.body_angles["l_leg_layer"] = (cos(alpha_l_leg), sin(alpha_l_leg), cos(beta_l_leg), sin(beta_l_leg))

    def determine_faces(self):
        self.visible_faces = {
            "head": {"front": [], "back": {}},
            "torso": {"front": [], "back": {}},
            "torso_layer": {"front": [], "back": {}},
            "r_arm": {"front": [], "back": {}},
            "r_arm_layer": {"front": [], "back": {}},
            "l_arm": {"front": [], "back": {}},
            "l_arm_layer": {"front": [], "back": {}},
            "r_leg": {"front": [], "back": {}},
            "r_leg_layer": {"front": [], "back": {}},
            "l_leg": {"front": [], "back": {}},
            "l_leg_layer": {"front": [], "back": {}},
            "cape": {"front": [], "back": {}}
        }

        all_faces = ["back", "right", "top", "front", "left", "bottom"]

        for k, v in self.visible_faces.items():
            cube_max_depth_faces = None
            self.set_cube_points()

            for cube_point in self.cube_points:
                cube_point[0].pre_project(0, 0, 0, self.body_angles[k][0], self.body_angles[k][1],
                                          self.body_angles[k][2], self.body_angles[k][3])
                cube_point[0].project()

                if (not cube_max_depth_faces) or (cube_max_depth_faces[0].get_depth() > cube_point[0].get_depth()):
                    cube_max_depth_faces = cube_point

            v["back"] = cube_max_depth_faces[1]
            v["front"] = [face for face in all_faces if face not in v["back"]]

        self.front_faces = self.visible_faces["torso"]["front"]
        self.back_faces = [face for face in all_faces if face not in self.front_faces]

    def set_cube_points(self):
        self.cube_points.append(
            (
                Point(
                    self,
                    {
                        "x": 0,
                        "y": 0,
                        "z": 0
                    }
                ),
                ["back", "right", "top"]
            )
        )

        self.cube_points.append(
            (
                Point(
                    self,
                    {
                        "x": 0,
                        "y": 0,
                        "z": 1
                    }
                ),
                ["front", "right", "top"]
            )
        )

        self.cube_points.append(
            (
                Point(
                    self,
                    {
                        "x": 0,
                        "y": 1,
                        "z": 0
                    }
                ),
                ["back", "right", "bottom"]
            )
        )

        self.cube_points.append(
            (
                Point(
                    self,
                    {
                        "x": 0,
                        "y": 1,
                        "z": 1
                    }
                ),
                ["front", "right", "bottom"]
            )
        )

        self.cube_points.append(
            (
                Point(
                    self,
                    {
                        "x": 1,
                        "y": 0,
                        "z": 0
                    }
                ),
                ["back", "left", "top"]
            )
        )

        self.cube_points.append(
            (
                Point(
                    self,
                    {
                        "x": 1,
                        "y": 0,
                        "z": 1
                    }
                ),
                ["front", "left", "top"]
            )
        )

        self.cube_points.append(
            (
                Point(
                    self,
                    {
                        "x": 1,
                        "y": 1,
                        "z": 0
                    }
                ),
                ["back", "left", "bottom"]
            )
        )

        self.cube_points.append(
            (
                Point(
                    self,
                    {
                        "x": 1,
                        "y": 1,
                        "z": 1
                    }
                ),
                ["front", "left", "bottom"]
            )
        )

    def generate_polygons(self, hd_ratio, skin, im_cape):
        self.polygons = {
            "helmet": {"front": [], "back": [], "top": [], "bottom": [], "right": [], "left": []},
            "head": {"front": [], "back": [], "top": [], "bottom": [], "right": [], "left": []},
            "torso": {"front": [], "back": [], "top": [], "bottom": [], "right": [], "left": []},
            "torso_layer": {"front": [], "back": [], "top": [], "bottom": [], "right": [], "left": []},
            "r_arm": {"front": [], "back": [], "top": [], "bottom": [], "right": [], "left": []},
            "r_arm_layer": {"front": [], "back": [], "top": [], "bottom": [], "right": [], "left": []},
            "l_arm": {"front": [], "back": [], "top": [], "bottom": [], "right": [], "left": []},
            "l_arm_layer": {"front": [], "back": [], "top": [], "bottom": [], "right": [], "left": []},
            "r_leg": {"front": [], "back": [], "top": [], "bottom": [], "right": [], "left": []},
            "r_leg_layer": {"front": [], "back": [], "top": [], "bottom": [], "right": [], "left": []},
            "l_leg": {"front": [], "back": [], "top": [], "bottom": [], "right": [], "left": []},
            "l_leg_layer": {"front": [], "back": [], "top": [], "bottom": [], "right": [], "left": []},
            "cape": {"front": [], "back": [], "top": [], "bottom": [], "right": [], "left": []}
        }

        """Head"""
        volume_points = {}
        for i in range(0, 9 * hd_ratio):
            for j in range(0, 9 * hd_ratio):
                volume_points = append_dict(volume_points, i, j, -2 * hd_ratio,
                                            Point(self, {"x": i, "y": j, "z": -2 * hd_ratio}))
                volume_points = append_dict(volume_points, i, j, 6 * hd_ratio,
                                            Point(self, {"x": i, "y": j, "z": 6 * hd_ratio}))

        for j in range(0, 9 * hd_ratio):
            for k in range(-2 * hd_ratio, 7 * hd_ratio):
                volume_points = append_dict(volume_points, 0, j, k, Point(self, {"x": 0, "y": j, "z": k}))
                volume_points = append_dict(volume_points, 8 * hd_ratio, j, k,
                                            Point(self, {"x": 8 * hd_ratio, "y": j, "z": k}))

        for i in range(0, 9 * hd_ratio):
            for k in range(-2 * hd_ratio, 7 * hd_ratio):
                volume_points = append_dict(volume_points, i, 0, k, Point(self, {"x": i, "y": 0, "z": k}))
                volume_points = append_dict(volume_points, i, 8 * hd_ratio, k,
                                            Point(self, {"x": i, "y": 8 * hd_ratio, "z": k}))

        if "back" in self.visible_faces["head"]["front"]:
            for i in range(0, 8 * hd_ratio):
                for j in range(0, 8 * hd_ratio):
                    color = skin.getpixel((32 * hd_ratio - 1 - i, 8 * hd_ratio + j))
                    if color[3] != 0:
                        self.polygons["head"]["back"].append(Polygon([
                            volume_points[i][j][-2 * hd_ratio],
                            volume_points[i + 1][j][-2 * hd_ratio],
                            volume_points[i + 1][j + 1][-2 * hd_ratio],
                            volume_points[i][j + 1][-2 * hd_ratio]],
                            color))

        if "front" in self.visible_faces["head"]["front"]:
            for i in range(0, 8 * hd_ratio):
                for j in range(0, 8 * hd_ratio):
                    color = skin.getpixel((8 * hd_ratio + i, 8 * hd_ratio + j))
                    if color[3] != 0:
                        self.polygons["head"]["front"].append(Polygon([
                            volume_points[i][j][6 * hd_ratio],
                            volume_points[i + 1][j][6 * hd_ratio],
                            volume_points[i + 1][j + 1][6 * hd_ratio],
                            volume_points[i][j + 1][6 * hd_ratio]],
                            color))

        if "right" in self.visible_faces["head"]["front"]:
            for j in range(0, 8 * hd_ratio):
                for k in range(-2 * hd_ratio, 6 * hd_ratio):
                    color = skin.getpixel((k + 2 * hd_ratio, 8 * hd_ratio + j))
                    if color[3] != 0:
                        self.polygons["head"]["right"].append(Polygon([
                            volume_points[0][j][k],
                            volume_points[0][j][k + 1],
                            volume_points[0][j + 1][k + 1],
                            volume_points[0][j + 1][k]],
                            color))

        if "left" in self.visible_faces["head"]["front"]:
            for j in range(0, 8 * hd_ratio):
                for k in range(-2 * hd_ratio, 6 * hd_ratio):
                    color = skin.getpixel(((24 * hd_ratio - 1) - k - 2 * hd_ratio, 8 * hd_ratio + j))
                    if color[3] != 0:
                        self.polygons["head"]["left"].append(Polygon([
                            volume_points[8 * hd_ratio][j][k],
                            volume_points[8 * hd_ratio][j][k + 1],
                            volume_points[8 * hd_ratio][j + 1][k + 1],
                            volume_points[8 * hd_ratio][j + 1][k]],
                            color))

        if "top" in self.visible_faces["head"]["front"]:
            for i in range(0, 8 * hd_ratio):
                for k in range(-2 * hd_ratio, 6 * hd_ratio):
                    color = skin.getpixel((8 * hd_ratio + i, 2 * hd_ratio + k))
                    if color[3] != 0:
                        self.polygons["head"]["top"].append(Polygon([
                            volume_points[i][0][k],
                            volume_points[i + 1][0][k],
                            volume_points[i + 1][0][k + 1],
                            volume_points[i][0][k + 1]],
                            color))

        if "bottom" in self.visible_faces["head"]["front"]:
            for i in range(0, 8 * hd_ratio):
                for k in range(-2 * hd_ratio, 6 * hd_ratio):
                    color = skin.getpixel((16 * hd_ratio + i, 2 * hd_ratio + k))
                    if color[3] != 0:
                        self.polygons["head"]["bottom"].append(Polygon([
                            volume_points[i][8 * hd_ratio][k],
                            volume_points[i + 1][8 * hd_ratio][k],
                            volume_points[i + 1][8 * hd_ratio][k + 1],
                            volume_points[i][8 * hd_ratio][k + 1]],
                            color))

        """Helmet / Hair"""
        if self.display_hair:
            volume_points = {}
            for i in range(0, 9 * hd_ratio):
                for j in range(0, 9 * hd_ratio):
                    volume_points = append_dict(volume_points, i, j, -2 * hd_ratio,
                                                Point(self, {"x": i * 8.5 / 8 - 0.25 * hd_ratio,
                                                             "y": j * 8.5 / 8 - 0.25 * hd_ratio,
                                                             "z": -2.25 * hd_ratio}))
                    volume_points = append_dict(volume_points, i, j, 6 * hd_ratio,
                                                Point(self, {"x": i * 8.5 / 8 - 0.25 * hd_ratio,
                                                             "y": j * 8.5 / 8 - 0.25 * hd_ratio,
                                                             "z": 6.25 * hd_ratio}))

            for j in range(0, 9 * hd_ratio):
                for k in range(-2 * hd_ratio, 7 * hd_ratio):
                    volume_points = append_dict(volume_points, 0, j, k,
                                                Point(self, {"x": -0.25 * hd_ratio,
                                                             "y": j * 8.5 / 8 - 0.25 * hd_ratio,
                                                             "z": k * 8.5 / 8 - 0.25 * hd_ratio}))
                    volume_points = append_dict(volume_points, 8 * hd_ratio, j, k,
                                                Point(self, {"x": 8.25 * hd_ratio,
                                                             "y": j * 8.5 / 8 - 0.25 * hd_ratio,
                                                             "z": k * 8.5 / 8 - 0.25 * hd_ratio}))

            for i in range(0, 9 * hd_ratio):
                for k in range(-2 * hd_ratio, 7 * hd_ratio):
                    volume_points = append_dict(volume_points, i, 0, k,
                                                Point(self, {"x": i * 8.5 / 8 - 0.25 * hd_ratio,
                                                             "y": -0.25 * hd_ratio,
                                                             "z": k * 8.5 / 8 - 0.25 * hd_ratio}))
                    volume_points = append_dict(volume_points, i, 8 * hd_ratio, k,
                                                Point(self, {"x": i * 8.5 / 8 - 0.25 * hd_ratio,
                                                             "y": 8.25 * hd_ratio,
                                                             "z": k * 8.5 / 8 - 0.25 * hd_ratio}))

            for i in range(0, 8 * hd_ratio):
                for j in range(0, 8 * hd_ratio):
                    color = skin.getpixel((64 * hd_ratio - 1 - i, 8 * hd_ratio + j))
                    if color[3] != 0:
                        self.polygons["helmet"]["back"].append(Polygon([
                            volume_points[i][j][-2 * hd_ratio],
                            volume_points[i + 1][j][-2 * hd_ratio],
                            volume_points[i + 1][j + 1][-2 * hd_ratio],
                            volume_points[i][j + 1][-2 * hd_ratio]],
                            color))

            for i in range(0, 8 * hd_ratio):
                for j in range(0, 8 * hd_ratio):
                    color = skin.getpixel((40 * hd_ratio + i, 8 * hd_ratio + j))
                    if color[3] != 0:
                        self.polygons["helmet"]["front"].append(Polygon([
                            volume_points[i][j][6 * hd_ratio],
                            volume_points[i + 1][j][6 * hd_ratio],
                            volume_points[i + 1][j + 1][6 * hd_ratio],
                            volume_points[i][j + 1][6 * hd_ratio]],
                            color))

            for j in range(0, 8 * hd_ratio):
                for k in range(-2 * hd_ratio, 6 * hd_ratio):
                    color = skin.getpixel((34 * hd_ratio + k, 8 * hd_ratio + j))
                    if color[3] != 0:
                        self.polygons["helmet"]["right"].append(Polygon([
                            volume_points[0][j][k],
                            volume_points[0][j][k + 1],
                            volume_points[0][j + 1][k + 1],
                            volume_points[0][j + 1][k]],
                            color))

            for j in range(0, 8 * hd_ratio):
                for k in range(-2 * hd_ratio, 6 * hd_ratio):
                    color = skin.getpixel((54 * hd_ratio - k - 1, 8 * hd_ratio + j))
                    if color[3] != 0:
                        self.polygons["helmet"]["left"].append(Polygon([
                            volume_points[8 * hd_ratio][j][k],
                            volume_points[8 * hd_ratio][j][k + 1],
                            volume_points[8 * hd_ratio][j + 1][k + 1],
                            volume_points[8 * hd_ratio][j + 1][k]],
                            color))

            for i in range(0, 8 * hd_ratio):
                for k in range(-2 * hd_ratio, 6 * hd_ratio):
                    color = skin.getpixel((40 * hd_ratio + i, 2 * hd_ratio + k))
                    if color[3] != 0:
                        self.polygons["helmet"]["top"].append(Polygon([
                            volume_points[i][0][k],
                            volume_points[i + 1][0][k],
                            volume_points[i + 1][0][k + 1],
                            volume_points[i][0][k + 1]],
                            color))

            for i in range(0, 8 * hd_ratio):
                for k in range(-2 * hd_ratio, 6 * hd_ratio):
                    color = skin.getpixel((48 * hd_ratio + 1, 2 * hd_ratio + k))
                    if color[3] != 0:
                        self.polygons["helmet"]["bottom"].append(Polygon([
                            volume_points[i][8 * hd_ratio][k],
                            volume_points[i + 1][8 * hd_ratio][k],
                            volume_points[i + 1][8 * hd_ratio][k + 1],
                            volume_points[i][8 * hd_ratio][k + 1]],
                            color))

        if not self.head_only:
            """Torso"""
            volume_points = {}
            for i in range(0, 9 * hd_ratio):
                for j in range(0, 13 * hd_ratio):
                    volume_points = append_dict(volume_points, i, j, 0,
                                                Point(self, {"x": i, "y": j + 8 * hd_ratio, "z": 0}))
                    volume_points = append_dict(volume_points, i, j, 4 * hd_ratio,
                                                Point(self, {"x": i, "y": j + 8 * hd_ratio, "z": 4 * hd_ratio}))

            for j in range(0, 13 * hd_ratio):
                for k in range(0, 5 * hd_ratio):
                    volume_points = append_dict(volume_points, 0, j, k,
                                                Point(self, {"x": 0, "y": j + 8 * hd_ratio, "z": k}))
                    volume_points = append_dict(volume_points, 8 * hd_ratio, j, k,
                                                Point(self, {"x": 8 * hd_ratio, "y": j + 8 * hd_ratio, "z": k}))

            for i in range(0, 9 * hd_ratio):
                for k in range(0, 5 * hd_ratio):
                    volume_points = append_dict(volume_points, i, 0, k,
                                                Point(self, {"x": i, "y": 8 * hd_ratio, "z": k}))
                    volume_points = append_dict(volume_points, i, 12 * hd_ratio, k,
                                                Point(self, {"x": i, "y": 20 * hd_ratio, "z": k}))

            if "back" in self.visible_faces["torso"]["front"]:
                for i in range(0, 8 * hd_ratio):
                    for j in range(0, 12 * hd_ratio):
                        color = skin.getpixel(((40 * hd_ratio - 1) - i, 20 * hd_ratio + j))
                        if color[3] != 0:
                            self.polygons["torso"]["back"].append(Polygon([
                                volume_points[i][j][0],
                                volume_points[i + 1][j][0],
                                volume_points[i + 1][j + 1][0],
                                volume_points[i][j + 1][0]],
                                color))

            if "front" in self.visible_faces["torso"]["front"]:
                for i in range(0, 8 * hd_ratio):
                    for j in range(0, 12 * hd_ratio):
                        color = skin.getpixel((20 * hd_ratio + i, 20 * hd_ratio + j))
                        if color[3] != 0:
                            self.polygons["torso"]["front"].append(Polygon([
                                volume_points[i][j][4 * hd_ratio],
                                volume_points[i + 1][j][4 * hd_ratio],
                                volume_points[i + 1][j + 1][4 * hd_ratio],
                                volume_points[i][j + 1][4 * hd_ratio]],
                                color))

            if "right" in self.visible_faces["torso"]["front"]:
                for j in range(0, 12 * hd_ratio):
                    for k in range(0 * hd_ratio, 4 * hd_ratio):
                        color = skin.getpixel((16 * hd_ratio + k, 20 * hd_ratio + j))
                        if color[3] != 0:
                            self.polygons["torso"]["right"].append(Polygon([
                                volume_points[0][j][k],
                                volume_points[0][j][k + 1],
                                volume_points[0][j + 1][k + 1],
                                volume_points[0][j + 1][k]],
                                color))

            if "left" in self.visible_faces["torso"]["front"]:
                for j in range(0, 12 * hd_ratio):
                    for k in range(0 * hd_ratio, 4 * hd_ratio):
                        color = skin.getpixel(((32 * hd_ratio - 1) - k, 20 * hd_ratio + j))
                        if color[3] != 0:
                            self.polygons["torso"]["left"].append(Polygon([
                                volume_points[8 * hd_ratio][j][k],
                                volume_points[8 * hd_ratio][j][k + 1],
                                volume_points[8 * hd_ratio][j + 1][k + 1],
                                volume_points[8 * hd_ratio][j + 1][k]],
                                color))

            if "top" in self.visible_faces["torso"]["front"]:
                for i in range(0, 8 * hd_ratio):
                    for k in range(0 * hd_ratio, 4 * hd_ratio):
                        color = skin.getpixel((20 * hd_ratio + i, 16 * hd_ratio + k))
                        if color[3] != 0:
                            self.polygons["torso"]["top"].append(Polygon([
                                volume_points[i][0][k],
                                volume_points[i + 1][0][k],
                                volume_points[i + 1][0][k + 1],
                                volume_points[i][0][k + 1]],
                                color))

            if "bottom" in self.visible_faces["torso"]["front"]:
                for i in range(0, 8 * hd_ratio):
                    for k in range(0 * hd_ratio, 4 * hd_ratio):
                        color = skin.getpixel((28 * hd_ratio + i, (20 * hd_ratio - 1) - k))
                        if color[3] != 0:
                            self.polygons["torso"]["bottom"].append(Polygon([
                                volume_points[i][12 * hd_ratio][k],
                                volume_points[i + 1][12 * hd_ratio][k],
                                volume_points[i + 1][12 * hd_ratio][k + 1],
                                volume_points[i][12 * hd_ratio][k + 1]],
                                color))

            """Torso 2nd layer"""
            if self.layers:
                volume_points = {}
                for i in range(0, 9 * hd_ratio):
                    for j in range(0, 13 * hd_ratio):
                        volume_points = append_dict(volume_points, i, j, 0,
                                                    Point(self, {"x": i * 8.25 / 8 - 0.125 * hd_ratio,
                                                                 "y": (j * 12.25 / 12 - 0.125 * hd_ratio) + 8 * hd_ratio,
                                                                 "z": -0.125 * hd_ratio}))
                        volume_points = append_dict(volume_points, i, j, 4 * hd_ratio,
                                                    Point(self, {"x": i * 8.25 / 8 - 0.125 * hd_ratio,
                                                                 "y": (j * 12.25 / 12 - 0.125 * hd_ratio) + 8 * hd_ratio,
                                                                 "z": 4.125 * hd_ratio}))

                for j in range(0, 13 * hd_ratio):
                    for k in range(0, 5 * hd_ratio):
                        volume_points = append_dict(volume_points, 0, j, k,
                                                    Point(self, {"x": -0.125 * hd_ratio,
                                                                 "y": (j * 12.25 / 12 - 0.125 * hd_ratio) + 8 * hd_ratio,
                                                                 "z": k * 4.25 / 4 - 0.125 * hd_ratio}))
                        volume_points = append_dict(volume_points, 8 * hd_ratio, j, k,
                                                    Point(self, {"x": 8.125 * hd_ratio,
                                                                 "y": (j * 12.25 / 12 - 0.125 * hd_ratio) + 8 * hd_ratio,
                                                                 "z": k * 4.25 / 4 - 0.125 * hd_ratio}))

                for i in range(0, 9 * hd_ratio):
                    for k in range(0, 5 * hd_ratio):
                        volume_points = append_dict(volume_points, i, 0, k,
                                                    Point(self, {"x": i * 8.25 / 8 - 0.125 * hd_ratio,
                                                                 "y": 7.875 * hd_ratio,
                                                                 "z": k * 4.25 / 4 - 0.125 * hd_ratio}))
                        volume_points = append_dict(volume_points, i, 12 * hd_ratio, k,
                                                    Point(self, {"x": i * 8.25 / 8 - 0.125 * hd_ratio,
                                                                 "y": 20.125 * hd_ratio,
                                                                 "z": k * 4.25 / 4 - 0.125 * hd_ratio}))

                if "back" in self.visible_faces["torso_layer"]["front"]:
                    for i in range(0, 8 * hd_ratio):
                        for j in range(0, 12 * hd_ratio):
                            color = skin.getpixel(((40 * hd_ratio - 1) - i, 20 * hd_ratio + j + 16))
                            if color[3] != 0:
                                self.polygons["torso_layer"]["back"].append(Polygon([
                                    volume_points[i][j][0],
                                    volume_points[i + 1][j][0],
                                    volume_points[i + 1][j + 1][0],
                                    volume_points[i][j + 1][0]],
                                    color))

                if "front" in self.visible_faces["torso_layer"]["front"]:
                    for i in range(0, 8 * hd_ratio):
                        for j in range(0, 12 * hd_ratio):
                            color = skin.getpixel((20 * hd_ratio + i, 20 * hd_ratio + j + 16))
                            if color[3] != 0:
                                self.polygons["torso_layer"]["front"].append(Polygon([
                                    volume_points[i][j][4 * hd_ratio],
                                    volume_points[i + 1][j][4 * hd_ratio],
                                    volume_points[i + 1][j + 1][4 * hd_ratio],
                                    volume_points[i][j + 1][4 * hd_ratio]],
                                    color))

                if "right" in self.visible_faces["torso_layer"]["front"]:
                    for j in range(0, 12 * hd_ratio):
                        for k in range(0 * hd_ratio, 4 * hd_ratio):
                            color = skin.getpixel((16 * hd_ratio + k, 20 * hd_ratio + j + 16))
                            if color[3] != 0:
                                self.polygons["torso_layer"]["right"].append(Polygon([
                                    volume_points[0][j][k],
                                    volume_points[0][j][k + 1],
                                    volume_points[0][j + 1][k + 1],
                                    volume_points[0][j + 1][k]],
                                    color))

                if "left" in self.visible_faces["torso_layer"]["front"]:
                    for j in range(0, 12 * hd_ratio):
                        for k in range(0 * hd_ratio, 4 * hd_ratio):
                            color = skin.getpixel(((32 * hd_ratio - 1) - k, 20 * hd_ratio + j + 16))
                            if color[3] != 0:
                                self.polygons["torso_layer"]["left"].append(Polygon([
                                    volume_points[8 * hd_ratio][j][k],
                                    volume_points[8 * hd_ratio][j][k + 1],
                                    volume_points[8 * hd_ratio][j + 1][k + 1],
                                    volume_points[8 * hd_ratio][j + 1][k]],
                                    color))

                if "top" in self.visible_faces["torso_layer"]["front"]:
                    for i in range(0, 8 * hd_ratio):
                        for k in range(0 * hd_ratio, 4 * hd_ratio):
                            color = skin.getpixel((20 * hd_ratio + i, 16 * hd_ratio + k + 16))
                            if color[3] != 0:
                                self.polygons["torso_layer"]["top"].append(Polygon([
                                    volume_points[i][0][k],
                                    volume_points[i + 1][0][k],
                                    volume_points[i + 1][0][k + 1],
                                    volume_points[i][0][k + 1]],
                                    color))

                if "bottom" in self.visible_faces["torso_layer"]["front"]:
                    for i in range(0, 8 * hd_ratio):
                        for k in range(0 * hd_ratio, 4 * hd_ratio):
                            color = skin.getpixel((28 * hd_ratio + i, (20 * hd_ratio - 1) - k + 16))
                            if color[3] != 0:
                                self.polygons["torso_layer"]["bottom"].append(Polygon([
                                    volume_points[i][12 * hd_ratio][k],
                                    volume_points[i + 1][12 * hd_ratio][k],
                                    volume_points[i + 1][12 * hd_ratio][k + 1],
                                    volume_points[i][12 * hd_ratio][k + 1]],
                                    color))

            """Cape"""
            if self.display_cape:
                volume_points = {}
                for i in range(0, 11 * hd_ratio):
                    for j in range(0, 17 * hd_ratio):
                        volume_points = append_dict(volume_points, i, j, 0,
                                                    Point(self, {"x": i - 1, "y": j + 8 * hd_ratio, "z": -1}))
                        volume_points = append_dict(volume_points, i, j, 1 * hd_ratio,
                                                    Point(self, {"x": i - 1, "y": j + 8 * hd_ratio, "z": 0 * hd_ratio}))

                for j in range(0, 17 * hd_ratio):
                    for k in range(0, 2 * hd_ratio):
                        volume_points = append_dict(volume_points, 0, j, k,
                                                    Point(self, {"x": 0, "y": j + 8 * hd_ratio, "z": k}))
                        volume_points = append_dict(volume_points, 8 * hd_ratio, j, k,
                                                    Point(self, {"x": 8 * hd_ratio, "y": j + 8 * hd_ratio, "z": k}))

                for i in range(0, 11 * hd_ratio):
                    for k in range(0, 2 * hd_ratio):
                        volume_points = append_dict(volume_points, i, 0, k,
                                                    Point(self, {"x": i, "y": 8 * hd_ratio, "z": k}))
                        volume_points = append_dict(volume_points, i, 12 * hd_ratio, k,
                                                    Point(self, {"x": i, "y": 20 * hd_ratio, "z": k}))

                if "back" in self.visible_faces["cape"]["front"]:
                    for i in range(0, 10 * hd_ratio):
                        for j in range(0, 16 * hd_ratio):
                            color = im_cape.getpixel(((11 * hd_ratio - 1) - i, 1 * hd_ratio + j))
                            if color[3] != 0:
                                self.polygons["cape"]["back"].append(Polygon([
                                    volume_points[i][j][0],
                                    volume_points[i + 1][j][0],
                                    volume_points[i + 1][j + 1][0],
                                    volume_points[i][j + 1][0]],
                                    color))

                if "front" in self.visible_faces["cape"]["front"]:
                    for i in range(0, 10 * hd_ratio):
                        for j in range(0, 16 * hd_ratio):
                            color = im_cape.getpixel((12 * hd_ratio + i, 1 * hd_ratio + j))
                            if color[3] != 0:
                                self.polygons["cape"]["front"].append(Polygon([
                                    volume_points[i][j][1 * hd_ratio],
                                    volume_points[i + 1][j][1 * hd_ratio],
                                    volume_points[i + 1][j + 1][1 * hd_ratio],
                                    volume_points[i][j + 1][1 * hd_ratio]],
                                    color))

                if "right" in self.visible_faces["cape"]["front"]:
                    for j in range(0, 16 * hd_ratio):
                        color = im_cape.getpixel((12 * hd_ratio, 1 * hd_ratio + j))
                        if color[3] != 0:
                            self.polygons["cape"]["right"].append(Polygon([
                                volume_points[0][j][0],
                                volume_points[0][j][1],
                                volume_points[0][j + 1][1],
                                volume_points[0][j + 1][0]],
                                color))

                if "left" in self.visible_faces["cape"]["front"]:
                    for j in range(0, 16 * hd_ratio):
                        color = im_cape.getpixel((1 * hd_ratio, 1 * hd_ratio + j))
                        if color[3] != 0:
                            self.polygons["cape"]["left"].append(Polygon([
                                volume_points[10 * hd_ratio][j][0],
                                volume_points[10 * hd_ratio][j][1],
                                volume_points[10 * hd_ratio][j + 1][1],
                                volume_points[10 * hd_ratio][j + 1][0]],
                                color))

                if "top" in self.visible_faces["cape"]["front"]:
                    for i in range(0, 10 * hd_ratio):
                        color = im_cape.getpixel((1 + i, 0))
                        if color[3] != 0:
                            self.polygons["cape"]["top"].append(Polygon([
                                volume_points[i][0][0],
                                volume_points[i + 1][0][0],
                                volume_points[i + 1][0][1],
                                volume_points[i][0][1]],
                                color))

                if "bottom" in self.visible_faces["cape"]["front"]:
                    for i in range(0, 10 * hd_ratio):
                        color = im_cape.getpixel((11 * hd_ratio + i, 0))
                        if color[3] != 0:
                            self.polygons["cape"]["bottom"].append(Polygon([
                                volume_points[i][16 * hd_ratio][0],
                                volume_points[i + 1][16 * hd_ratio][0],
                                volume_points[i + 1][16 * hd_ratio][1],
                                volume_points[i][16 * hd_ratio][1]],
                                color))

            start = 1 if self.player.is_slim else 0
            """Right arm"""
            volume_points = {}
            for i in range(start, 5 * hd_ratio):
                for j in range(0, 13 * hd_ratio):
                    volume_points = append_dict(volume_points, i, j, 0,
                                                Point(self, {"x": i - 4 * hd_ratio, "y": j + 8 * hd_ratio, "z": 0}))
                    volume_points = append_dict(volume_points, i, j, 4 * hd_ratio,
                                                Point(self, {"x": i - 4 * hd_ratio, "y": j + 8 * hd_ratio, "z": 4 * hd_ratio}))

            for j in range(0, 13 * hd_ratio):
                for k in range(0, 5 * hd_ratio):
                    volume_points = append_dict(volume_points, start, j, k,
                                                Point(self, {"x": -4 * hd_ratio + start, "y": j + 8 * hd_ratio, "z": k}))
                    volume_points = append_dict(volume_points, 4 * hd_ratio, j, k,
                                                Point(self, {"x": 0, "y": j + 8 * hd_ratio, "z": k}))

            for i in range(start, 5 * hd_ratio):
                for k in range(0, 5 * hd_ratio):
                    volume_points = append_dict(volume_points, i, 0, k,
                                                Point(self, {"x": i - 4 * hd_ratio, "y": 8 * hd_ratio, "z": k}))
                    volume_points = append_dict(volume_points, i, 12 * hd_ratio, k,
                                                Point(self, {"x": i - 4 * hd_ratio, "y": 20 * hd_ratio, "z": k}))

            if "back" in self.visible_faces["r_arm"]["front"]:
                for i in range(start, 4 * hd_ratio):
                    for j in range(0, 12 * hd_ratio):
                        color = skin.getpixel((((56 - start) * hd_ratio - 1) - i, 20 * hd_ratio + j))
                        if color[3] != 0:
                            self.polygons["r_arm"]["back"].append(Polygon([
                                volume_points[i][j][0],
                                volume_points[i + 1][j][0],
                                volume_points[i + 1][j + 1][0],
                                volume_points[i][j + 1][0]],
                                color))

            if "front" in self.visible_faces["r_arm"]["front"]:
                for i in range(start, 4 * hd_ratio):
                    for j in range(0, 12 * hd_ratio):
                        color = skin.getpixel(((44 - start) * hd_ratio + i, 20 * hd_ratio + j))
                        if color[3] != 0:
                            self.polygons["r_arm"]["front"].append(Polygon([
                                volume_points[i][j][4 * hd_ratio],
                                volume_points[i + 1][j][4 * hd_ratio],
                                volume_points[i + 1][j + 1][4 * hd_ratio],
                                volume_points[i][j + 1][4 * hd_ratio]],
                                color))

            if "right" in self.visible_faces["r_arm"]["front"]:
                for j in range(0, 12 * hd_ratio):
                    for k in range(0, 4 * hd_ratio):
                        color = skin.getpixel((40 * hd_ratio + k, 20 * hd_ratio + j))
                        if color[3] != 0:
                            self.polygons["r_arm"]["right"].append(Polygon([
                                volume_points[start][j][k],
                                volume_points[start][j][k + 1],
                                volume_points[start][j + 1][k + 1],
                                volume_points[start][j + 1][k]],
                                color))

            if "left" in self.visible_faces["r_arm"]["front"]:
                for j in range(0, 12 * hd_ratio):
                    for k in range(0, 4 * hd_ratio):
                        color = skin.getpixel((((52 - start) * hd_ratio - 1) - k, 20 * hd_ratio + j))
                        if color[3] != 0:
                            self.polygons["r_arm"]["left"].append(Polygon([
                                volume_points[4 * hd_ratio][j][k],
                                volume_points[4 * hd_ratio][j][k + 1],
                                volume_points[4 * hd_ratio][j + 1][k + 1],
                                volume_points[4 * hd_ratio][j + 1][k]],
                                color))

            if "top" in self.visible_faces["r_arm"]["front"]:
                for i in range(start, 4 * hd_ratio):
                    for k in range(0, 4 * hd_ratio):
                        color = skin.getpixel(((44 - start) * hd_ratio + i, 16 * hd_ratio + k))
                        if color[3] != 0:
                            self.polygons["r_arm"]["top"].append(Polygon([
                                volume_points[i][0][k],
                                volume_points[i + 1][0][k],
                                volume_points[i + 1][0][k + 1],
                                volume_points[i][0][k + 1]],
                                color))

            if "bottom" in self.visible_faces["r_arm"]["front"]:
                for i in range(start, 4 * hd_ratio):
                    for k in range(0, 4 * hd_ratio):
                        color = skin.getpixel(((48 - start * 2) * hd_ratio + i, 16 * hd_ratio + k))
                        if color[3] != 0:
                            self.polygons["r_arm"]["bottom"].append(Polygon([
                                volume_points[i][12 * hd_ratio][k],
                                volume_points[i + 1][12 * hd_ratio][k],
                                volume_points[i + 1][12 * hd_ratio][k + 1],
                                volume_points[i][12 * hd_ratio][k + 1]],
                                color))

            """Right arm 2nd layer"""
            if self.layers:
                volume_points = {}
                for i in range(start, 5 * hd_ratio):
                    for j in range(0, 13 * hd_ratio):
                        volume_points = append_dict(volume_points, i, j, 0,
                                                    Point(self, {"x": (i * 4.25 / 4 - 0.125 * hd_ratio) - 4 * hd_ratio,
                                                                 "y": (j * 12.25 / 12 - 0.125 * hd_ratio) + 8 * hd_ratio,
                                                                 "z": -0.125 * hd_ratio}))
                        volume_points = append_dict(volume_points, i, j, 4 * hd_ratio,
                                                    Point(self, {"x": (i * 4.25 / 4 - 0.125 * hd_ratio) - 4 * hd_ratio,
                                                                 "y": (j * 12.25 / 12 - 0.125 * hd_ratio) + 8 * hd_ratio,
                                                                 "z": 4.125 * hd_ratio}))

                for j in range(0, 13 * hd_ratio):
                    for k in range(0, 5 * hd_ratio):
                        volume_points = append_dict(volume_points, start, j, k,
                                                    Point(self, {"x": (-4.125 + start) * hd_ratio,
                                                                 "y": (j * 12.25 / 12 - 0.125 * hd_ratio) + 8 * hd_ratio,
                                                                 "z": k * 4.25 / 4 - 0.125 * hd_ratio}))
                        volume_points = append_dict(volume_points, 4 * hd_ratio, j, k,
                                                    Point(self, {"x": 0.125 * hd_ratio,
                                                                 "y": (j * 12.25 / 12 - 0.125 * hd_ratio) + 8 * hd_ratio,
                                                                 "z": k * 4.25 / 4 - 0.125 * hd_ratio}))

                for i in range(start, 5 * hd_ratio):
                    for k in range(0, 5 * hd_ratio):
                        volume_points = append_dict(volume_points, i, 0, k,
                                                    Point(self, {"x": (i * 4.25 / 4 - 0.125 * hd_ratio) - 4 * hd_ratio,
                                                                 "y": 7.875 * hd_ratio,
                                                                 "z": k * 4.25 / 4 - 0.125 * hd_ratio}))
                        volume_points = append_dict(volume_points, i, 12 * hd_ratio, k,
                                                    Point(self, {"x": (i * 4.25 / 4 - 0.125 * hd_ratio) - 4 * hd_ratio,
                                                                 "y": 20.125 * hd_ratio,
                                                                 "z": k * 4.25 / 4 - 0.125 * hd_ratio}))

                if "back" in self.visible_faces["r_arm_layer"]["front"]:
                    for i in range(start, 4 * hd_ratio):
                        for j in range(0, 12 * hd_ratio):
                            color = skin.getpixel((((56 - start * 2) * hd_ratio - 1) - i, 20 * hd_ratio + j + 16))
                            if color[3] != 0:
                                self.polygons["r_arm_layer"]["back"].append(Polygon([
                                    volume_points[i][j][0],
                                    volume_points[i + 1][j][0],
                                    volume_points[i + 1][j + 1][0],
                                    volume_points[i][j + 1][0]],
                                    color))

                if "front" in self.visible_faces["r_arm_layer"]["front"]:
                    for i in range(start, 4 * hd_ratio):
                        for j in range(0, 12 * hd_ratio):
                            color = skin.getpixel(((44 - start) * hd_ratio + i, 20 * hd_ratio + j + 16))
                            if color[3] != 0:
                                self.polygons["r_arm_layer"]["front"].append(Polygon([
                                    volume_points[i][j][4 * hd_ratio],
                                    volume_points[i + 1][j][4 * hd_ratio],
                                    volume_points[i + 1][j + 1][4 * hd_ratio],
                                    volume_points[i][j + 1][4 * hd_ratio]],
                                    color))

                if "right" in self.visible_faces["r_arm_layer"]["front"]:
                    for j in range(0, 12 * hd_ratio):
                        for k in range(0, 4 * hd_ratio):
                            color = skin.getpixel((40 * hd_ratio + k, 20 * hd_ratio + j + 16))
                            if color[3] != 0:
                                self.polygons["r_arm_layer"]["right"].append(Polygon([
                                    volume_points[start][j][k],
                                    volume_points[start][j][k + 1],
                                    volume_points[start][j + 1][k + 1],
                                    volume_points[start][j + 1][k]],
                                    color))

                if "left" in self.visible_faces["r_arm_layer"]["front"]:
                    for j in range(0, 12 * hd_ratio):
                        for k in range(0, 4 * hd_ratio):
                            color = skin.getpixel((((52 - start) * hd_ratio - 1) - k, 20 * hd_ratio + j + 16))
                            if color[3] != 0:
                                self.polygons["r_arm_layer"]["left"].append(Polygon([
                                    volume_points[4 * hd_ratio][j][k],
                                    volume_points[4 * hd_ratio][j][k + 1],
                                    volume_points[4 * hd_ratio][j + 1][k + 1],
                                    volume_points[4 * hd_ratio][j + 1][k]],
                                    color))

                if "top" in self.visible_faces["r_arm_layer"]["front"]:
                    for i in range(start, 4 * hd_ratio):
                        for k in range(0, 4 * hd_ratio):
                            color = skin.getpixel(((44 - start) * hd_ratio + i, 16 * hd_ratio + k + 16))
                            if color[3] != 0:
                                self.polygons["r_arm_layer"]["top"].append(Polygon([
                                    volume_points[i][0][k],
                                    volume_points[i + 1][0][k],
                                    volume_points[i + 1][0][k + 1],
                                    volume_points[i][0][k + 1]],
                                    color))

                if "bottom" in self.visible_faces["r_arm_layer"]["front"]:
                    for i in range(start, 4 * hd_ratio):
                        for k in range(0, 4 * hd_ratio):
                            color = skin.getpixel(((48 - start * 2) * hd_ratio + i, 16 * hd_ratio + k + 16))
                            if color[3] != 0:
                                self.polygons["r_arm_layer"]["bottom"].append(Polygon([
                                    volume_points[i][12 * hd_ratio][k],
                                    volume_points[i + 1][12 * hd_ratio][k],
                                    volume_points[i + 1][12 * hd_ratio][k + 1],
                                    volume_points[i][12 * hd_ratio][k + 1]],
                                    color))

            """Left arm"""
            volume_points = {}
            for i in range(0, (5 - start) * hd_ratio):
                for j in range(0, 13 * hd_ratio):
                    volume_points = append_dict(volume_points, i, j, 0,
                                                Point(self, {"x": i + 8 * hd_ratio, "y": j + 8 * hd_ratio, "z": 0}))
                    volume_points = append_dict(volume_points, i, j, 4 * hd_ratio,
                                                Point(self, {"x": i + 8 * hd_ratio, "y": j + 8 * hd_ratio, "z": 4 * hd_ratio}))

            for j in range(0, 13 * hd_ratio):
                for k in range(0, 5 * hd_ratio):
                    volume_points = append_dict(volume_points, 0, j, k,
                                                Point(self, {"x": 8 * hd_ratio, "y": j + 8 * hd_ratio, "z": k}))
                    volume_points = append_dict(volume_points, (4 - start) * hd_ratio, j, k,
                                                Point(self, {"x": (12 - start) * hd_ratio, "y": j + 8 * hd_ratio, "z": k}))

            for i in range(0, (5 - start) * hd_ratio):
                for k in range(0, 5 * hd_ratio):
                    volume_points = append_dict(volume_points, i, 0, k,
                                                Point(self, {"x": i + 8 * hd_ratio, "y": 8 * hd_ratio, "z": k}))
                    volume_points = append_dict(volume_points, i, 12 * hd_ratio, k,
                                                Point(self, {"x": i + 8 * hd_ratio, "y": 20 * hd_ratio, "z": k}))

            if "back" in self.visible_faces["l_arm"]["front"]:
                for i in range(0, (4 - start) * hd_ratio):
                    for j in range(0, 12 * hd_ratio):
                        color = skin.getpixel(((48 - start * 2) * hd_ratio - 1 - i, 52 * hd_ratio + j))
                        if color[3] != 0:
                            self.polygons["l_arm"]["back"].append(Polygon([
                                volume_points[i][j][0],
                                volume_points[i + 1][j][0],
                                volume_points[i + 1][j + 1][0],
                                volume_points[i][j + 1][0]],
                                color))

            if "front" in self.visible_faces["l_arm"]["front"]:
                for i in range(0, (4 - start) * hd_ratio):
                    for j in range(0, 12 * hd_ratio):
                        color = skin.getpixel((36 * hd_ratio + i, 52 * hd_ratio + j))
                        if color[3] != 0:
                            self.polygons["l_arm"]["front"].append(Polygon([
                                volume_points[i][j][4 * hd_ratio],
                                volume_points[i + 1][j][4 * hd_ratio],
                                volume_points[i + 1][j + 1][4 * hd_ratio],
                                volume_points[i][j + 1][4 * hd_ratio]],
                                color))

            if "right" in self.visible_faces["l_arm"]["front"]:
                for j in range(0, 12 * hd_ratio):
                    for k in range(0, 4 * hd_ratio):
                        color = skin.getpixel((32 * hd_ratio + k, 52 * hd_ratio + j))
                        if color[3] != 0:
                            self.polygons["l_arm"]["right"].append(Polygon([
                                volume_points[0][j][k],
                                volume_points[0][j][k + 1],
                                volume_points[0][j + 1][k + 1],
                                volume_points[0][j + 1][k]],
                                color))

            if "left" in self.visible_faces["l_arm"]["front"]:
                for j in range(0, 12 * hd_ratio):
                    for k in range(0, 4 * hd_ratio):
                        color = skin.getpixel(((44 - start) * hd_ratio - 1 - k, 52 * hd_ratio + j))
                        if color[3] != 0:
                            self.polygons["l_arm"]["left"].append(Polygon([
                                volume_points[(4 - start) * hd_ratio][j][k],
                                volume_points[(4 - start) * hd_ratio][j][k + 1],
                                volume_points[(4 - start) * hd_ratio][j + 1][k + 1],
                                volume_points[(4 - start) * hd_ratio][j + 1][k]],
                                color))

            if "top" in self.visible_faces["l_arm"]["front"]:
                for i in range(0, (4 - start) * hd_ratio):
                    for k in range(0, 4 * hd_ratio):
                        color = skin.getpixel((36 * hd_ratio + i, 48 * hd_ratio + k))
                        if color[3] != 0:
                            self.polygons["l_arm"]["top"].append(Polygon([
                                volume_points[i][0][k],
                                volume_points[i + 1][0][k],
                                volume_points[i + 1][0][k + 1],
                                volume_points[i][0][k + 1]],
                                color))

            if "bottom" in self.visible_faces["l_arm"]["front"]:
                for i in range(0, (4 - start) * hd_ratio):
                    for k in range(0, 4 * hd_ratio):
                        color = skin.getpixel(((40 - start) * hd_ratio + i, 48 * hd_ratio + k))
                        if color[3] != 0:
                            self.polygons["l_arm"]["bottom"].append(Polygon([
                                volume_points[i][12 * hd_ratio][k],
                                volume_points[i + 1][12 * hd_ratio][k],
                                volume_points[i + 1][12 * hd_ratio][k + 1],
                                volume_points[i][12 * hd_ratio][k + 1]],
                                color))

            """Left arm 2nd layer"""
            if self.layers:
                volume_points = {}
                for i in range(0, (5 - start) * hd_ratio):
                    for j in range(0, 13 * hd_ratio):
                        volume_points = append_dict(volume_points, i, j, 0,
                                                    Point(self, {"x": (i * 4.25 / 4 - 0.125 * hd_ratio) + 8 * hd_ratio,
                                                                 "y": (j * 12.25 / 12 - 0.125 * hd_ratio) + 8 * hd_ratio,
                                                                 "z": -0.125 * hd_ratio}))
                        volume_points = append_dict(volume_points, i, j, 4 * hd_ratio,
                                                    Point(self, {"x": (i * 4.25 / 4 - 0.125 * hd_ratio) + 8 * hd_ratio,
                                                                 "y": (j * 12.25 / 12 - 0.125 * hd_ratio) + 8 * hd_ratio,
                                                                 "z": 4.125 * hd_ratio}))

                for j in range(0, 13 * hd_ratio):
                    for k in range(0, 5 * hd_ratio):
                        volume_points = append_dict(volume_points, 0, j, k,
                                                    Point(self, {"x": 7.875 * hd_ratio,
                                                                 "y": (j * 12.25 / 12 - 0.125 * hd_ratio) + 8 * hd_ratio,
                                                                 "z": k * 4.25 / 4 - 0.125 * hd_ratio}))
                        volume_points = append_dict(volume_points, (4 - start) * hd_ratio, j, k,
                                                    Point(self, {"x": (12.125 - start) * hd_ratio,
                                                                 "y": (j * 12.25 / 12 - 0.125 * hd_ratio) + 8 * hd_ratio,
                                                                 "z": k * 4.25 / 4 - 0.125 * hd_ratio}))

                for i in range(0, (5 - start) * hd_ratio):
                    for k in range(0, 5 * hd_ratio):
                        volume_points = append_dict(volume_points, i, 0, k,
                                                    Point(self, {"x": (i * 4.25 / 4 - 0.125 * hd_ratio) + 8 * hd_ratio,
                                                                 "y": 7.875 * hd_ratio,
                                                                 "z": k * 4.25 / 4 - 0.125 * hd_ratio}))
                        volume_points = append_dict(volume_points, i, 12 * hd_ratio, k,
                                                    Point(self, {"x": (i * 4.25 / 4 - 0.125 * hd_ratio) + 8 * hd_ratio,
                                                                 "y": 20.125 * hd_ratio,
                                                                 "z": k * 4.25 / 4 - 0.125 * hd_ratio}))

                if "back" in self.visible_faces["l_arm_layer"]["front"]:
                    for i in range(0, (4 - start) * hd_ratio):
                        for j in range(0, 12 * hd_ratio):
                            color = skin.getpixel(((64 - start * 2) * hd_ratio - 1 - i, 52 * hd_ratio + j))
                            if color[3] != 0:
                                self.polygons["l_arm_layer"]["back"].append(Polygon([
                                    volume_points[i][j][0],
                                    volume_points[i + 1][j][0],
                                    volume_points[i + 1][j + 1][0],
                                    volume_points[i][j + 1][0]],
                                    color))

                if "front" in self.visible_faces["l_arm_layer"]["front"]:
                    for i in range(0, (4 - start) * hd_ratio):
                        for j in range(0, 12 * hd_ratio):
                            color = skin.getpixel((52 * hd_ratio + i, 52 * hd_ratio + j))
                            if color[3] != 0:
                                self.polygons["l_arm_layer"]["front"].append(Polygon([
                                    volume_points[i][j][4 * hd_ratio],
                                    volume_points[i + 1][j][4 * hd_ratio],
                                    volume_points[i + 1][j + 1][4 * hd_ratio],
                                    volume_points[i][j + 1][4 * hd_ratio]],
                                    color))

                if "right" in self.visible_faces["l_arm_layer"]["front"]:
                    for j in range(0, 12 * hd_ratio):
                        for k in range(0, 4 * hd_ratio):
                            color = skin.getpixel((48 * hd_ratio + k, 52 * hd_ratio + j))
                            if color[3] != 0:
                                self.polygons["l_arm_layer"]["right"].append(Polygon([
                                    volume_points[0][j][k],
                                    volume_points[0][j][k + 1],
                                    volume_points[0][j + 1][k + 1],
                                    volume_points[0][j + 1][k]],
                                    color))

                if "left" in self.visible_faces["l_arm_layer"]["front"]:
                    for j in range(0, 12 * hd_ratio):
                        for k in range(0, 4 * hd_ratio):
                            color = skin.getpixel(((60 - start) * hd_ratio - 1 - k, 52 * hd_ratio + j))
                            if color[3] != 0:
                                self.polygons["l_arm_layer"]["left"].append(Polygon([
                                    volume_points[(4 - start) * hd_ratio][j][k],
                                    volume_points[(4 - start) * hd_ratio][j][k + 1],
                                    volume_points[(4 - start) * hd_ratio][j + 1][k + 1],
                                    volume_points[(4 - start) * hd_ratio][j + 1][k]],
                                    color))

                if "top" in self.visible_faces["l_arm_layer"]["front"]:
                    for i in range(0, (4 - start) * hd_ratio):
                        for k in range(0, 4 * hd_ratio):
                            color = skin.getpixel((52 * hd_ratio + i, 48 * hd_ratio + k))
                            if color[3] != 0:
                                self.polygons["l_arm_layer"]["top"].append(Polygon([
                                    volume_points[i][0][k],
                                    volume_points[i + 1][0][k],
                                    volume_points[i + 1][0][k + 1],
                                    volume_points[i][0][k + 1]],
                                    color))

                if "bottom" in self.visible_faces["l_arm_layer"]["front"]:
                    for i in range(0, (4 - start) * hd_ratio):
                        for k in range(0, 4 * hd_ratio):
                            color = skin.getpixel(((56 - start) * hd_ratio + i, 48 * hd_ratio + k))
                            if color[3] != 0:
                                self.polygons["l_arm_layer"]["bottom"].append(Polygon([
                                    volume_points[i][12 * hd_ratio][k],
                                    volume_points[i + 1][12 * hd_ratio][k],
                                    volume_points[i + 1][12 * hd_ratio][k + 1],
                                    volume_points[i][12 * hd_ratio][k + 1]],
                                    color))

            """Right leg"""
            volume_points = {}
            for i in range(0, 5 * hd_ratio):
                for j in range(0, 13 * hd_ratio):
                    volume_points = append_dict(volume_points, i, j, 0,
                                                Point(self, {"x": i, "y": j + 20 * hd_ratio, "z": 0}))
                    volume_points = append_dict(volume_points, i, j, 4 * hd_ratio,
                                                Point(self, {"x": i, "y": j + 20 * hd_ratio, "z": 4 * hd_ratio}))

            for j in range(0, 13 * hd_ratio):
                for k in range(0, 5 * hd_ratio):
                    volume_points = append_dict(volume_points, 0, j, k,
                                                Point(self, {"x": 0, "y": j + 20 * hd_ratio, "z": k}))
                    volume_points = append_dict(volume_points, 4 * hd_ratio, j, k,
                                                Point(self, {"x": 4 * hd_ratio, "y": j + 20 * hd_ratio, "z": k}))

            for i in range(0, 5 * hd_ratio):
                for k in range(0, 5 * hd_ratio):
                    volume_points = append_dict(volume_points, i, 0, k,
                                                Point(self, {"x": i, "y": 20 * hd_ratio, "z": k}))
                    volume_points = append_dict(volume_points, i, 12 * hd_ratio, k,
                                                Point(self, {"x": i, "y": 32 * hd_ratio, "z": k}))

            if "back" in self.visible_faces["r_leg"]["front"]:
                for i in range(0, 4 * hd_ratio):
                    for j in range(0, 12 * hd_ratio):
                        color = skin.getpixel(((16 * hd_ratio - 1) - i, 20 * hd_ratio + j))
                        if color[3] != 0:
                            self.polygons["r_leg"]["back"].append(Polygon([
                                volume_points[i][j][0],
                                volume_points[i + 1][j][0],
                                volume_points[i + 1][j + 1][0],
                                volume_points[i][j + 1][0]],
                                color))

            if "front" in self.visible_faces["r_leg"]["front"]:
                for i in range(0, 4 * hd_ratio):
                    for j in range(0, 12 * hd_ratio):
                        color = skin.getpixel((4 * hd_ratio + i, 20 * hd_ratio + j))
                        if color[3] != 0:
                            self.polygons["r_leg"]["front"].append(Polygon([
                                volume_points[i][j][4 * hd_ratio],
                                volume_points[i + 1][j][4 * hd_ratio],
                                volume_points[i + 1][j + 1][4 * hd_ratio],
                                volume_points[i][j + 1][4 * hd_ratio]],
                                color))

            if "right" in self.visible_faces["r_leg"]["front"]:
                for j in range(0, 12 * hd_ratio):
                    for k in range(0, 4 * hd_ratio):
                        color = skin.getpixel((k, 20 * hd_ratio + j))
                        if color[3] != 0:
                            self.polygons["r_leg"]["right"].append(Polygon([
                                volume_points[0][j][k],
                                volume_points[0][j][k + 1],
                                volume_points[0][j + 1][k + 1],
                                volume_points[0][j + 1][k]],
                                color))

            if "left" in self.visible_faces["r_leg"]["front"]:
                for j in range(0, 12 * hd_ratio):
                    for k in range(0, 4 * hd_ratio):
                        color = skin.getpixel(((12 * hd_ratio - 1) - k, 20 * hd_ratio + j))
                        if color[3] != 0:
                            self.polygons["r_leg"]["left"].append(Polygon([
                                volume_points[4 * hd_ratio][j][k],
                                volume_points[4 * hd_ratio][j][k + 1],
                                volume_points[4 * hd_ratio][j + 1][k + 1],
                                volume_points[4 * hd_ratio][j + 1][k]],
                                color))

            if "top" in self.visible_faces["r_leg"]["front"]:
                for i in range(0, 4 * hd_ratio):
                    for k in range(0, 4 * hd_ratio):
                        color = skin.getpixel((4 * hd_ratio + i, 16 * hd_ratio + k))
                        if color[3] != 0:
                            self.polygons["r_leg"]["top"].append(Polygon([
                                volume_points[i][0][k],
                                volume_points[i + 1][0][k],
                                volume_points[i + 1][0][k + 1],
                                volume_points[i][0][k + 1]],
                                color))

            if "bottom" in self.visible_faces["r_leg"]["front"]:
                for i in range(0, 4 * hd_ratio):
                    for k in range(0, 4 * hd_ratio):
                        color = skin.getpixel((8 * hd_ratio + i, 16 * hd_ratio + k))
                        if color[3] != 0:
                            self.polygons["r_leg"]["bottom"].append(Polygon([
                                volume_points[i][12 * hd_ratio][k],
                                volume_points[i + 1][12 * hd_ratio][k],
                                volume_points[i + 1][12 * hd_ratio][k + 1],
                                volume_points[i][12 * hd_ratio][k + 1]],
                                color))

            """Right leg 2nd layer"""
            if self.layers:
                volume_points = {}
                for i in range(0, 5 * hd_ratio):
                    for j in range(0, 13 * hd_ratio):
                        volume_points = append_dict(volume_points, i, j, 0,
                                                    Point(self, {"x": i * 4.25 / 4 - 0.125 * hd_ratio,
                                                                 "y": (j * 12.25 / 12 - 0.125 * hd_ratio) + 20 * hd_ratio,
                                                                 "z": -0.125 * hd_ratio}))
                        volume_points = append_dict(volume_points, i, j, 4 * hd_ratio,
                                                    Point(self, {"x": i * 4.25 / 4 - 0.125 * hd_ratio,
                                                                 "y": (j * 12.25 / 12 - 0.125 * hd_ratio) + 20 * hd_ratio,
                                                                 "z": 4.125 * hd_ratio}))

                for j in range(0, 13 * hd_ratio):
                    for k in range(0, 5 * hd_ratio):
                        volume_points = append_dict(volume_points, 0, j, k,
                                                    Point(self, {"x": -0.125 * hd_ratio,
                                                                 "y": (j * 12.25 / 12 - 0.125 * hd_ratio) + 20 * hd_ratio,
                                                                 "z": k * 4.25 / 4 - 0.125 * hd_ratio}))
                        volume_points = append_dict(volume_points, 4 * hd_ratio, j, k,
                                                    Point(self, {"x": 4.125 * hd_ratio,
                                                                 "y": (j * 12.25 / 12 - 0.125 * hd_ratio) + 20 * hd_ratio,
                                                                 "z": k * 4.25 / 4 - 0.125 * hd_ratio}))

                for i in range(0, 5 * hd_ratio):
                    for k in range(0, 5 * hd_ratio):
                        volume_points = append_dict(volume_points, i, 0, k,
                                                    Point(self, {"x": i * 4.25 / 4 - 0.125 * hd_ratio,
                                                                 "y": 19.875 * hd_ratio,
                                                                 "z": k * 4.25 / 4 - 0.125 * hd_ratio}))
                        volume_points = append_dict(volume_points, i, 12 * hd_ratio, k,
                                                    Point(self, {"x": i * 4.25 / 4 - 0.125 * hd_ratio,
                                                                 "y": 32.125 * hd_ratio,
                                                                 "z": k * 4.25 / 4 - 0.125 * hd_ratio}))

                if "back" in self.visible_faces["r_leg_layer"]["front"]:
                    for i in range(0, 4 * hd_ratio):
                        for j in range(0, 12 * hd_ratio):
                            color = skin.getpixel((16 * hd_ratio - 1 - i, 36 * hd_ratio + j))
                            if color[3] != 0:
                                self.polygons["r_leg_layer"]["back"].append(Polygon([
                                    volume_points[i][j][0],
                                    volume_points[i + 1][j][0],
                                    volume_points[i + 1][j + 1][0],
                                    volume_points[i][j + 1][0]],
                                    color))

                if "front" in self.visible_faces["r_leg_layer"]["front"]:
                    for i in range(0, 4 * hd_ratio):
                        for j in range(0, 12 * hd_ratio):
                            color = skin.getpixel((4 * hd_ratio + i, 36 * hd_ratio + j))
                            if color[3] != 0:
                                self.polygons["r_leg_layer"]["front"].append(Polygon([
                                    volume_points[i][j][4 * hd_ratio],
                                    volume_points[i + 1][j][4 * hd_ratio],
                                    volume_points[i + 1][j + 1][4 * hd_ratio],
                                    volume_points[i][j + 1][4 * hd_ratio]],
                                    color))

                if "right" in self.visible_faces["r_leg_layer"]["front"]:
                    for j in range(0, 12 * hd_ratio):
                        for k in range(0, 4 * hd_ratio):
                            color = skin.getpixel((k, 36 * hd_ratio + j))
                            if color[3] != 0:
                                self.polygons["r_leg_layer"]["right"].append(Polygon([
                                    volume_points[0][j][k],
                                    volume_points[0][j][k + 1],
                                    volume_points[0][j + 1][k + 1],
                                    volume_points[0][j + 1][k]],
                                    color))

                if "left" in self.visible_faces["r_leg_layer"]["front"]:
                    for j in range(0, 12 * hd_ratio):
                        for k in range(0, 4 * hd_ratio):
                            color = skin.getpixel((12 * hd_ratio - 1 - k, 36 * hd_ratio + j))
                            if color[3] != 0:
                                self.polygons["r_leg_layer"]["left"].append(Polygon([
                                    volume_points[4 * hd_ratio][j][k],
                                    volume_points[4 * hd_ratio][j][k + 1],
                                    volume_points[4 * hd_ratio][j + 1][k + 1],
                                    volume_points[4 * hd_ratio][j + 1][k]],
                                    color))

                if "top" in self.visible_faces["r_leg_layer"]["front"]:
                    for i in range(0, 4 * hd_ratio):
                        for k in range(0, 4 * hd_ratio):
                            color = skin.getpixel((4 * hd_ratio + i, 32 * hd_ratio + k))
                            if color[3] != 0:
                                self.polygons["r_leg_layer"]["top"].append(Polygon([
                                    volume_points[i][0][k],
                                    volume_points[i + 1][0][k],
                                    volume_points[i + 1][0][k + 1],
                                    volume_points[i][0][k + 1]],
                                    color))

                if "bottom" in self.visible_faces["r_leg_layer"]["front"]:
                    for i in range(0, 4 * hd_ratio):
                        for k in range(0, 4 * hd_ratio):
                            color = skin.getpixel((8 * hd_ratio + i, 32 * hd_ratio + k))
                            if color[3] != 0:
                                self.polygons["r_leg_layer"]["bottom"].append(Polygon([
                                    volume_points[i][12 * hd_ratio][k],
                                    volume_points[i + 1][12 * hd_ratio][k],
                                    volume_points[i + 1][12 * hd_ratio][k + 1],
                                    volume_points[i][12 * hd_ratio][k + 1]],
                                    color))

            """Left leg"""
            volume_points = {}
            for i in range(0, 9 * hd_ratio):
                for j in range(0, 13 * hd_ratio):
                    volume_points = append_dict(volume_points, i, j, 0,
                                                Point(self, {"x": i + 4 * hd_ratio,
                                                             "y": j + 20 * hd_ratio,
                                                             "z": 0}))
                    volume_points = append_dict(volume_points, i, j, 4 * hd_ratio,
                                                Point(self, {"x": i + 4 * hd_ratio,
                                                             "y": j + 20 * hd_ratio,
                                                             "z": 4 * hd_ratio}))

            for j in range(0, 13 * hd_ratio):
                for k in range(0, 5 * hd_ratio):
                    volume_points = append_dict(volume_points, 0, j, k,
                                                Point(self, {"x": 4 * hd_ratio, "y": j + 20 * hd_ratio, "z": k}))
                    volume_points = append_dict(volume_points, 4 * hd_ratio, j, k,
                                                Point(self, {"x": 8 * hd_ratio, "y": j + 20 * hd_ratio, "z": k}))

            for i in range(0, 9 * hd_ratio):
                for k in range(0, 5 * hd_ratio):
                    volume_points = append_dict(volume_points, i, 0, k,
                                                Point(self, {"x": i + 4 * hd_ratio, "y": 20 * hd_ratio, "z": k}))
                    volume_points = append_dict(volume_points, i, 12 * hd_ratio, k,
                                                Point(self, {"x": i + 4 * hd_ratio, "y": 32 * hd_ratio, "z": k}))

            if "back" in self.visible_faces["l_leg"]["front"]:
                for i in range(0, 4 * hd_ratio):
                    for j in range(0, 12 * hd_ratio):
                        color = skin.getpixel((32 * hd_ratio - 1 - i, 52 * hd_ratio + j))
                        if color[3] != 0:
                            self.polygons["l_leg"]["back"].append(Polygon([
                                volume_points[i][j][0],
                                volume_points[i + 1][j][0],
                                volume_points[i + 1][j + 1][0],
                                volume_points[i][j + 1][0]],
                                color))

            if "front" in self.visible_faces["l_leg"]["front"]:
                for i in range(0, 4 * hd_ratio):
                    for j in range(0, 12 * hd_ratio):
                        color = skin.getpixel((20 * hd_ratio + i, 52 * hd_ratio + j))
                        if color[3] != 0:
                            self.polygons["l_leg"]["front"].append(Polygon([
                                volume_points[i][j][4 * hd_ratio],
                                volume_points[i + 1][j][4 * hd_ratio],
                                volume_points[i + 1][j + 1][4 * hd_ratio],
                                volume_points[i][j + 1][4 * hd_ratio]],
                                color))

            if "right" in self.visible_faces["l_leg"]["front"]:
                for j in range(0, 12 * hd_ratio):
                    for k in range(0, 4 * hd_ratio):
                        color = skin.getpixel((16 * hd_ratio + k, 52 * hd_ratio + j))
                        if color[3] != 0:
                            self.polygons["l_leg"]["right"].append(Polygon([
                                volume_points[0][j][k],
                                volume_points[0][j][k + 1],
                                volume_points[0][j + 1][k + 1],
                                volume_points[0][j + 1][k]],
                                color))

            if "left" in self.visible_faces["l_leg"]["front"]:
                for j in range(0, 12 * hd_ratio):
                    for k in range(0, 4 * hd_ratio):
                        color = skin.getpixel((28 * hd_ratio - 1 - k, 52 * hd_ratio + j))
                        if color[3] != 0:
                            self.polygons["l_leg"]["left"].append(Polygon([
                                volume_points[4 * hd_ratio][j][k],
                                volume_points[4 * hd_ratio][j][k + 1],
                                volume_points[4 * hd_ratio][j + 1][k + 1],
                                volume_points[4 * hd_ratio][j + 1][k]],
                                color))

            if "top" in self.visible_faces["l_leg"]["front"]:
                for i in range(0, 4 * hd_ratio):
                    for k in range(0, 4 * hd_ratio):
                        color = skin.getpixel((20 * hd_ratio + i, 48 * hd_ratio + k))
                        if color[3] != 0:
                            self.polygons["l_leg"]["top"].append(Polygon([
                                volume_points[i][0][k],
                                volume_points[i + 1][0][k],
                                volume_points[i + 1][0][k + 1],
                                volume_points[i][0][k + 1]],
                                color))

            if "bottom" in self.visible_faces["l_leg"]["front"]:
                for i in range(0, 4 * hd_ratio):
                    for k in range(0, 4 * hd_ratio):
                        color = skin.getpixel((24 * hd_ratio + i, 48 * hd_ratio + k))
                        if color[3] != 0:
                            self.polygons["l_leg"]["bottom"].append(Polygon([
                                volume_points[i][12 * hd_ratio][k],
                                volume_points[i + 1][12 * hd_ratio][k],
                                volume_points[i + 1][12 * hd_ratio][k + 1],
                                volume_points[i][12 * hd_ratio][k + 1]],
                                color))

            """Left leg 2nd layer"""
            if self.layers:
                volume_points = {}
                for i in range(0, 5 * hd_ratio):
                    for j in range(0, 13 * hd_ratio):
                        volume_points = append_dict(volume_points, i, j, 0,
                                                    Point(self, {"x": (i * 4.25 / 4 - 0.125 * hd_ratio) + 4 * hd_ratio,
                                                                 "y": (j * 12.25 / 12 - 0.125 * hd_ratio) + 20 * hd_ratio,
                                                                 "z": -0.125 * hd_ratio}))
                        volume_points = append_dict(volume_points, i, j, 4 * hd_ratio,
                                                    Point(self, {"x": (i * 4.25 / 4 - 0.125 * hd_ratio) + 4 * hd_ratio,
                                                                 "y": (j * 12.25 / 12 - 0.125 * hd_ratio) + 20 * hd_ratio,
                                                                 "z": 4.125 * hd_ratio}))

                for j in range(0, 13 * hd_ratio):
                    for k in range(0, 5 * hd_ratio):
                        volume_points = append_dict(volume_points, 0, j, k,
                                                    Point(self, {"x": 3.875 * hd_ratio,
                                                                 "y": (j * 12.25 / 12 - 0.125 * hd_ratio) + 20 * hd_ratio,
                                                                 "z": k * 4.25 / 4 - 0.125 * hd_ratio}))
                        volume_points = append_dict(volume_points, 4 * hd_ratio, j, k,
                                                    Point(self, {"x": 8.125 * hd_ratio,
                                                                 "y": (j * 12.25 / 12 - 0.125 * hd_ratio) + 20 * hd_ratio,
                                                                 "z": k * 4.25 / 4 - 0.125 * hd_ratio}))

                for i in range(0, 5 * hd_ratio):
                    for k in range(0, 5 * hd_ratio):
                        volume_points = append_dict(volume_points, i, 0, k,
                                                    Point(self, {"x": (i * 4.25 / 4 - 0.125 * hd_ratio) + 4 * hd_ratio,
                                                                 "y": 19.875 * hd_ratio,
                                                                 "z": k * 4.25 / 4 - 0.125 * hd_ratio}))
                        volume_points = append_dict(volume_points, i, 12 * hd_ratio, k,
                                                    Point(self, {"x": (i * 4.25 / 4 - 0.125 * hd_ratio) + 4 * hd_ratio,
                                                                 "y": 32.125 * hd_ratio,
                                                                 "z": k * 4.25 / 4 - 0.125 * hd_ratio}))

                if "back" in self.visible_faces["l_leg_layer"]["front"]:
                    for i in range(0, 4 * hd_ratio):
                        for j in range(0, 12 * hd_ratio):
                            color1 = skin.getpixel((16 * hd_ratio - 1 - i, 52 * hd_ratio + j))
                            if color1[3] != 0:
                                self.polygons["l_leg_layer"]["back"].append(Polygon([
                                    volume_points[i][j][0],
                                    volume_points[i + 1][j][0],
                                    volume_points[i + 1][j + 1][0],
                                    volume_points[i][j + 1][0]],
                                    color1))

                if "front" in self.visible_faces["l_leg_layer"]["front"]:
                    for i in range(0, 4 * hd_ratio):
                        for j in range(0, 12 * hd_ratio):
                            color2 = skin.getpixel((4 * hd_ratio + i, 52 * hd_ratio + j))
                            if color2[3] != 0:
                                self.polygons["l_leg_layer"]["front"].append(Polygon([
                                    volume_points[i][j][4 * hd_ratio],
                                    volume_points[i + 1][j][4 * hd_ratio],
                                    volume_points[i + 1][j + 1][4 * hd_ratio],
                                    volume_points[i][j + 1][4 * hd_ratio]],
                                    color2))

                if "right" in self.visible_faces["l_leg_layer"]["front"]:
                    for j in range(0, 12 * hd_ratio):
                        for k in range(0, 4 * hd_ratio):
                            color1 = skin.getpixel((k, 52 * hd_ratio + j))
                            if color1[3] != 0:
                                self.polygons["l_leg_layer"]["right"].append(Polygon([
                                    volume_points[0][j][k],
                                    volume_points[0][j][k + 1],
                                    volume_points[0][j + 1][k + 1],
                                    volume_points[0][j + 1][k]],
                                    color1))

                if "left" in self.visible_faces["l_leg_layer"]["front"]:
                    for j in range(0, 12 * hd_ratio):
                        for k in range(0, 4 * hd_ratio):
                            color2 = skin.getpixel((12 * hd_ratio - 1 - k, 52 * hd_ratio + j))
                            if color2[3] != 0:
                                self.polygons["l_leg_layer"]["left"].append(Polygon([
                                    volume_points[4 * hd_ratio][j][k],
                                    volume_points[4 * hd_ratio][j][k + 1],
                                    volume_points[4 * hd_ratio][j + 1][k + 1],
                                    volume_points[4 * hd_ratio][j + 1][k]],
                                    color2))

                if "top" in self.visible_faces["l_leg_layer"]["front"]:
                    for i in range(0, 4 * hd_ratio):
                        for k in range(0, 4 * hd_ratio):
                            color1 = skin.getpixel((4 * hd_ratio + i, 48 * hd_ratio + k))
                            if color1[3] != 0:
                                self.polygons["l_leg_layer"]["top"].append(Polygon([
                                    volume_points[i][0][k],
                                    volume_points[i + 1][0][k],
                                    volume_points[i + 1][0][k + 1],
                                    volume_points[i][0][k + 1]],
                                    color1))

                if "bottom" in self.visible_faces["l_leg_layer"]["front"]:
                    for i in range(0, 4 * hd_ratio):
                        for k in range(0, 4 * hd_ratio):
                            color2 = skin.getpixel((8 * hd_ratio + i, 48 * hd_ratio + k))
                            if color2[3] != 0:
                                self.polygons["l_leg_layer"]["bottom"].append(Polygon([
                                    volume_points[i][12 * hd_ratio][k],
                                    volume_points[i + 1][12 * hd_ratio][k],
                                    volume_points[i + 1][12 * hd_ratio][k + 1],
                                    volume_points[i][12 * hd_ratio][k + 1]],
                                    color2))

    def member_rotation(self, hd_ratio):
        for face in self.polygons["head"]:
            for poly in self.polygons["head"][face]:
                poly.pre_project(4 * hd_ratio, 8 * hd_ratio, 2 * hd_ratio, *self.body_angles["head"])

        if self.display_hair:
            for face in self.polygons["helmet"]:
                for poly in self.polygons["helmet"][face]:
                    poly.pre_project(4 * hd_ratio, 8 * hd_ratio, 2 * hd_ratio, *self.body_angles["head"])

        if not self.head_only:
            for face in self.polygons["cape"]:
                for poly in self.polygons["cape"][face]:
                    poly.pre_project(4 * hd_ratio, 8 * hd_ratio, 0 * hd_ratio, *self.body_angles["cape"])

            for face in self.polygons["r_arm"]:
                for poly in self.polygons["r_arm"][face]:
                    poly.pre_project(-2 * hd_ratio, 10 * hd_ratio, 2 * hd_ratio, *self.body_angles["r_arm"])

            for face in self.polygons["r_arm_layer"]:
                for poly in self.polygons["r_arm_layer"][face]:
                    poly.pre_project(-2 * hd_ratio, 10 * hd_ratio, 2 * hd_ratio, *self.body_angles["r_arm_layer"])

            for face in self.polygons["l_arm"]:
                for poly in self.polygons["l_arm"][face]:
                    poly.pre_project(10 * hd_ratio, 10 * hd_ratio, 2 * hd_ratio, *self.body_angles["l_arm"])

            for face in self.polygons["l_arm_layer"]:
                for poly in self.polygons["l_arm_layer"][face]:
                    poly.pre_project(10 * hd_ratio, 10 * hd_ratio, 2 * hd_ratio, *self.body_angles["l_arm_layer"])

            for face in self.polygons["r_leg"]:
                for poly in self.polygons["r_leg"][face]:
                    poly.pre_project(2 * hd_ratio, 22 * hd_ratio, 2 * hd_ratio, *self.body_angles["r_leg"])

            for face in self.polygons["r_leg_layer"]:
                for poly in self.polygons["r_leg_layer"][face]:
                    poly.pre_project(2 * hd_ratio, 22 * hd_ratio, 2 * hd_ratio, *self.body_angles["r_leg_layer"])

            for face in self.polygons["l_leg"]:
                for poly in self.polygons["l_leg"][face]:
                    poly.pre_project(6 * hd_ratio, 22 * hd_ratio, 2 * hd_ratio, *self.body_angles["l_leg"])

            for face in self.polygons["l_leg_layer"]:
                for poly in self.polygons["l_leg_layer"][face]:
                    poly.pre_project(6 * hd_ratio, 22 * hd_ratio, 2 * hd_ratio, *self.body_angles["l_leg_layer"])

    def create_project_plan(self):
        for piece in self.polygons:
            for face in self.polygons[piece]:
                for poly in self.polygons[piece][face]:
                    if not poly.is_projected:
                        poly.project()

    def display_image(self):
        width = self.max_x - self.min_x
        height = self.max_y - self.min_y
        ratio = self.ratio
        if ratio < 2:
            ratio = 2

        if self.aa:
            ratio *= 2

        src_width = ratio * width + 1
        src_height = ratio * height + 1
        real_width = src_width / 2
        real_height = src_height / 2

        image = Image.new('RGBA', (int(src_width), int(src_height)))

        display_order = self.get_display_order()
        draw = ImageDraw.Draw(image)
        for pieces in display_order:
            for piece, faces in pieces.items():
                for face in faces:
                    for poly in self.polygons[piece][face]:
                        poly.add_png_polygon(draw, self.min_x, self.min_y, ratio)

        if self.aa:
            image = image.resize((int(real_width), int(real_height)), resample=Image.LANCZOS)
        return image

    def get_display_order(self):
        display_order = []
        if "front" in self.front_faces:
            display_order.append({"cape": self.visible_faces["cape"]["front"]})

        if "top" in self.front_faces:
            if "right" in self.front_faces:
                display_order.append({"l_leg_layer": self.back_faces})
                display_order.append({"l_leg": self.visible_faces["l_leg"]["front"]})
                display_order.append({"l_leg_layer": self.visible_faces["l_leg"]["front"]})

                display_order.append({"r_leg_layer": self.back_faces})
                display_order.append({"r_leg": self.visible_faces["r_leg"]["front"]})
                display_order.append({"r_leg_layer": self.visible_faces["r_leg"]["front"]})

                display_order.append({"l_arm_layer": self.back_faces})
                display_order.append({"l_arm": self.visible_faces["l_arm"]["front"]})
                display_order.append({"l_arm_layer": self.visible_faces["l_arm"]["front"]})

                display_order.append({"torso_layer": self.back_faces})
                display_order.append({"torso": self.visible_faces["torso"]["front"]})
                display_order.append({"torso_layer": self.visible_faces["torso"]["front"]})

                display_order.append({"r_arm_layer": self.back_faces})
                display_order.append({"r_arm": self.visible_faces["r_arm"]["front"]})
                display_order.append({"r_arm_layer": self.visible_faces["r_arm"]["front"]})
            else:
                display_order.append({"r_leg_layer": self.back_faces})
                display_order.append({"r_leg": self.visible_faces["r_leg"]["front"]})
                display_order.append({"r_leg_layer": self.visible_faces["r_leg"]["front"]})

                display_order.append({"l_leg_layer": self.back_faces})
                display_order.append({"l_leg": self.visible_faces["l_leg"]["front"]})
                display_order.append({"l_leg_layer": self.visible_faces["l_leg"]["front"]})

                display_order.append({"r_arm_layer": self.back_faces})
                display_order.append({"r_arm": self.visible_faces["r_arm"]["front"]})
                display_order.append({"r_arm_layer": self.visible_faces["r_arm"]["front"]})

                display_order.append({"torso_layer": self.back_faces})
                display_order.append({"torso": self.visible_faces["torso"]["front"]})
                display_order.append({"torso_layer": self.visible_faces["torso"]["front"]})

                display_order.append({"l_arm_layer": self.back_faces})
                display_order.append({"l_arm": self.visible_faces["l_arm"]["front"]})
                display_order.append({"l_arm_layer": self.visible_faces["l_arm"]["front"]})

            if "back" in self.front_faces:
                display_order.append({"cape": self.visible_faces["cape"]["front"]})

            display_order.append({"helmet": self.back_faces})
            display_order.append({"head": self.visible_faces["head"]["front"]})
            display_order.append({"helmet": self.visible_faces["head"]["front"]})
        else:
            display_order.append({"helmet": self.back_faces})
            display_order.append({"head": self.visible_faces["head"]["front"]})
            display_order.append({"helmet": self.visible_faces["head"]["front"]})
            if "right" in self.front_faces:
                display_order.append({"l_arm_layer": self.back_faces})
                display_order.append({"l_arm": self.visible_faces["l_arm"]["front"]})
                display_order.append({"l_arm_layer": self.visible_faces["l_arm"]["front"]})

                display_order.append({"torso_layer": self.back_faces})
                display_order.append({"torso": self.visible_faces["torso"]["front"]})
                display_order.append({"torso_layer": self.visible_faces["torso"]["front"]})

                display_order.append({"r_arm_layer": self.back_faces})
                display_order.append({"r_arm": self.visible_faces["r_arm"]["front"]})
                display_order.append({"r_arm_layer": self.visible_faces["r_arm"]["front"]})

                display_order.append({"l_leg_layer": self.back_faces})
                display_order.append({"l_leg": self.visible_faces["l_leg"]["front"]})
                display_order.append({"l_leg_layer": self.visible_faces["l_leg"]["front"]})

                display_order.append({"r_leg_layer": self.back_faces})
                display_order.append({"r_leg": self.visible_faces["r_leg"]["front"]})
                display_order.append({"r_leg_layer": self.visible_faces["r_leg"]["front"]})
            else:
                display_order.append({"r_arm_layer": self.back_faces})
                display_order.append({"r_arm": self.visible_faces["r_arm"]["front"]})
                display_order.append({"r_arm_layer": self.visible_faces["r_arm"]["front"]})

                display_order.append({"torso_layer": self.back_faces})
                display_order.append({"torso": self.visible_faces["torso"]["front"]})
                display_order.append({"torso_layer": self.visible_faces["torso"]["front"]})

                display_order.append({"l_arm_layer": self.back_faces})
                display_order.append({"l_arm": self.visible_faces["l_arm"]["front"]})
                display_order.append({"l_arm_layer": self.visible_faces["l_arm"]["front"]})

                display_order.append({"r_leg_layer": self.back_faces})
                display_order.append({"r_leg": self.visible_faces["r_leg"]["front"]})
                display_order.append({"r_leg_layer": self.visible_faces["r_leg"]["front"]})

                display_order.append({"l_leg_layer": self.back_faces})
                display_order.append({"l_leg": self.visible_faces["l_leg"]["front"]})
                display_order.append({"l_leg_layer": self.visible_faces["l_leg"]["front"]})

            if "back" in self.front_faces:
                display_order.append({"cape": self.visible_faces["cape"]["front"]})

        return display_order


class Point:
    def __init__(self, super_cls, origin_coords, dest_coords={}, is_projected=False, is_pre_projected=False):
        self.dest_coords = dest_coords
        self.is_projected = is_projected
        self.is_pre_projected = is_pre_projected
        self.super = super_cls

        if (isinstance(origin_coords, dict)) and (len(origin_coords.keys()) == 3):
            x = origin_coords["x"] if not is_not_existing(origin_coords, "x") else 0
            y = origin_coords["y"] if not is_not_existing(origin_coords, "y") else 0
            z = origin_coords["z"] if not is_not_existing(origin_coords, "z") else 0
        else:
            x, y, z = 0, 0, 0

        self.origin_coords = {"x": x, "y": y, "z": z}

    def pre_project(self, dx, dy, dz, cos_a, sin_a, cos_b, sin_b):
        if not self.is_pre_projected:
            x = self.origin_coords["x"] - dx
            y = self.origin_coords["y"] - dy
            z = self.origin_coords["z"] - dz
            self.origin_coords["x"] = x * cos_b + z * sin_b + dx
            self.origin_coords["y"] = x * sin_a * sin_b + y * cos_a - z * sin_a * cos_b + dy
            self.origin_coords["z"] = -x * cos_a * sin_b + y * sin_a + z * cos_a * cos_b + dz
            self.is_pre_projected = True

    def project(self):
        x = self.origin_coords["x"]
        y = self.origin_coords["y"]
        z = self.origin_coords["z"]
        self.dest_coords = {}
        self.dest_coords["x"] = x * self.super.cos_b + z * self.super.sin_b
        self.dest_coords[
            "y"] = x * self.super.sin_a * self.super.sin_b + y * self.super.cos_a - z * self.super.sin_a * self.super.cos_b
        self.dest_coords[
            "z"] = -x * self.super.cos_a * self.super.sin_b + y * self.super.sin_a + z * self.super.cos_a * self.super.cos_b
        self.is_projected = True
        self.super.min_x = min(self.super.min_x, self.dest_coords["x"])
        self.super.max_x = max(self.super.max_x, self.dest_coords["x"])
        self.super.min_y = min(self.super.min_y, self.dest_coords["y"])
        self.super.max_y = max(self.super.max_y, self.dest_coords["y"])

    def get_depth(self):
        if not self.is_projected:
            self.project()
        return self.dest_coords["z"]

    def get_dest_coords(self):
        return self.dest_coords


class Polygon:
    def __init__(self, dots, color, is_projected=False, face="w", face_depth=0):
        self.face = face
        self.is_projected = is_projected
        self.face_depth = face_depth
        self.dots = dots
        self.color = color
        coord_0 = dots[0].origin_coords
        coord_1 = dots[1].origin_coords
        coord_2 = dots[2].origin_coords

        if (coord_0["x"] == coord_1["x"]) and (coord_1["x"] == coord_2["x"]):
            self.face = "x"
            self.face_depth = coord_0["x"]
        elif (coord_0["y"] == coord_1["y"]) and (coord_1["y"] == coord_2["y"]):
            self.face = "y"
            self.face_depth = coord_0["y"]
        elif (coord_0["z"] == coord_1["z"]) and (coord_1["z"] == coord_2["z"]):
            self.face = "z"
            self.face_depth = coord_0["z"]

    def add_png_polygon(self, draw, min_x, min_y, ratio):
        points_2d = []

        same_plan_x = True
        same_plan_y = True
        coord_x = None
        coord_y = None

        for dot in self.dots:
            coord = dot.dest_coords
            if not coord_x:
                coord_x = coord["x"]
            if not coord_y:
                coord_y = coord["y"]
            if coord_x != coord["x"]:
                same_plan_x = False
            if coord_y != coord["y"]:
                same_plan_y = False
            points_2d.append(((coord["x"] - min_x) * ratio, (coord["y"] - min_y) * ratio))

            if not (same_plan_x or same_plan_y):
                draw.polygon(points_2d, fill=self.color, outline=self.color)

    def project(self):
        for dot in self.dots:
            if not dot.is_projected:
                dot.project()
        self.is_projected = True

    def pre_project(self, dx, dy, dz, cos_a, sin_a, cos_b, sin_b):
        for dot in self.dots:
            dot.pre_project(dx, dy, dz, cos_a, sin_a, cos_b, sin_b)
