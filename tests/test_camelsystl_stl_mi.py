"""
Author: Lili Yu
Date: 2025-05-10 18:00:00
LastEditTime: 2025-05-10 18:00:00
LastEditors: Lili Yu
Description: test stl and mi module
"""

import pandas as pd
from hydrodataset import CamelsYstl
from torchhydro.datasets.mi_stl import STL, MutualInformation, Decomposition


def test_dataset():
    camelsystl = CamelsYstl()
    basin = camelsystl.gage
    print(basin)

class Ystl():
    def __init__(self):
        self.datasource = CamelsYstl()
        self.basin = ["1000",]
        self.time_range = ["1990-01-01","1994-01-01"]
        self.var_list = ["streamflow", "discharge_vol1", "discharge_vol2", "discharge_vol3",]
        self.pet_list = ["pet"]
        self.prcp_list = ["prcp"]
        self.streamflow = None
        self.prcp = None
        self.pet = None
        self.read_streamflow()
        self.read_prcp()
        self.read_pet()

    def read_streamflow(self):
        data = self.datasource.read_ts_xrdataset(
            self.basin,
            self.time_range,
            self.var_list,
        )
        data1 = data.streamflow.to_dataframe()
        data2 = data.discharge_vol1.to_dataframe()
        data3 = data.discharge_vol2.to_dataframe()
        data4 = data.discharge_vol3.to_dataframe()
        data1.drop(axis=0, index=("1000", "1992-02-29"), inplace=True)
        data2.drop(axis=0, index=("1000", "1992-02-29"), inplace=True)
        data3.drop(axis=0, index=("1000", "1992-02-29"), inplace=True)
        data4.drop(axis=0, index=("1000", "1992-02-29"), inplace=True)
        data1 = data1.values[:, 0]
        data2 = data2.values[:, 0]
        data3 = data3.values[:, 0]
        data4 = data4.values[:, 0]
        data_ = data1.tolist() + data2.tolist() + data3.tolist() + data4.tolist()
        self.streamflow = data_ + data_

    def read_pet(self):
        data = self.datasource.read_ts_xrdataset(
            self.basin,
            self.time_range,
            self.pet_list
        )
        data = data.pet.to_dataframe()
        data.drop(axis=0, index=("1000", "1992-02-29"), inplace=True)
        data = data.values[:, 0]
        pet = data.tolist() + data.tolist() + data.tolist() + data.tolist()
        self.pet = pet + pet

    def read_prcp(self):
        data = self.datasource.read_ts_xrdataset(
            self.basin,
            self.time_range,
            self.prcp_list
        )
        data = data.prcp.to_dataframe()
        data.drop(axis=0, index=("1000", "1992-02-29"), inplace=True)
        data = data.values[:, 0]
        prcp = data.tolist() + data.tolist() + data.tolist() + data.tolist()
        self.prcp = prcp + prcp

def test_read_data():
    x = Ystl().pet
    print(x)
# [165.8 164.1 158.8 ...  73.2  71.1  71.3]

def test_cycle_subseries():
    x = Ystl().pet
    stl = STL(x)
    stl._cycle_subseries(x)
    print(stl.cycle_subseries)
# PASSED                      [100%]365

def test_weight_function():
    u = [1, 0.5, 0, 0.5, 1]
    n = 5
    w = []
    stl = STL()
    for i in range(n):
        w_i = stl.weight_function(u[i], 3)
        w.append(w_i)
    print(w)
# [0, 0.5625, 1, 0.5625, 0]
# [0, 0.669921875, 1, 0.669921875, 0]

def test_extend_subseries():
    x = Ystl().pet
    stl = STL(x)
    subseries = stl._cycle_subseries(x)
    extend_subseries = stl._extend_subseries(subseries)
    print(len(extend_subseries))
    print(len(extend_subseries[0]))
# 365
# 18

def test_de_extend_subseries():
    x = Ystl().pet
    stl = STL(x)
    subseries = stl._cycle_subseries(x)
    extend_subseries = stl._extend_subseries(subseries)
    de_extend_subseries = stl._de_extend_subseries(extend_subseries)
    print(len(de_extend_subseries))
    print(len(de_extend_subseries[0]))
# 365
# 16

def test_recover_series():
    x = Ystl().pet
    stl = STL(x)
    stl._cycle_subseries(x)
    print(len(stl.cycle_subseries))
    series = stl._recover_series(stl.cycle_subseries)
    print(series[:10])
# 365
# [165.8, 164.1, 158.8, 158.0, 156.2, 144.8, 137.6, 134.6, 130.3, 128.2]

def test_neighborhood_weight():
    x = Ystl().pet
    stl = STL(x)
    i_focal = 3
    weight = stl._neighborhood_weight(13, i_focal=i_focal)
    print("i_focal = {}".format(i_focal))
    print(weight)
# i_focal = 0    PASSED                  [100%]
# [1.0, 0.9982648933890121, 0.9861753122936036, 0.9538536071777344, 0.8929533099629123, 0.7983059250581059, 0.669921875,
# 0.5148943256800089, 0.34847330183407005, 0.19322586059570312, 0.07477611946222622, 0.01212663499827988, 0]
# PASSED                  [100%]
# i_focal = 1
# [0.9977477485949877, 1.0, 0.9977477485949877, 0.9820766066349517, 0.9403696580985775, 0.8625726392333274,
# 0.7438883494722954, 0.5878823691852629, 0.40901258144152797, 0.23297940878706283, 0.09252419331977448,
# 0.01537976908411411, 0]
# PASSED                  [100%]
# i_focal = 2
# [0.976191488, 0.997002999, 1.0, 0.997002999, 0.976191488, 0.921167317, 0.8200258559999999, 0.669921875,
# 0.48189030400000005, 0.283593393, 0.11621427199999991, 0.01990251099999998, 0]
# PASSED                  [100%]i_focal = 3
# [0.8929533099629123, 0.9674381496121647, 0.9958904161106462, 1.0, 0.9958904161106462, 0.9674381496121647,
# 0.8929533099629123, 0.7590709148064702, 0.5687589331394396, 0.34847330183407005, 0.1484497016367144,
# 0.0263752519294353, 0]
# PASSED                  [100%]
# i_focal = 12
# [0, 0.01212663499827988, 0.07477611946222622, 0.19322586059570312, 0.34847330183407005, 0.5148943256800089,
# 0.669921875, 0.7983059250581059, 0.8929533099629123, 0.9538536071777344, 0.9861753122936036, 0.9982648933890121, 1.0]
# PASSED                  [100%]
# i_focal = 11
# [0, 0.01537976908411411, 0.09252419331977448, 0.23297940878706283, 0.40901258144152797, 0.5878823691852629,
# 0.7438883494722954, 0.8625726392333274, 0.9403696580985775, 0.9820766066349517, 0.9977477485949877,
# 1.0, 0.9977477485949877]
# PASSED                  [100%]
# i_focal = 10
# [0, 0.01990251099999998, 0.11621427199999991, 0.283593393, 0.48189030400000005, 0.669921875, 0.8200258559999999,
# 0.921167317, 0.976191488, 0.997002999, 1.0, 0.997002999, 0.976191488]

def test_moving_average_smoothing():
    x = Ystl().pet
    stl = STL(x)
    xx = [1, 5, 3, 9, 7, 13, 11, 17, 15, 21, 19, 25, 23, 29, 27, 33, 31]  # 17
    result = stl.moving_average_smoothing(7, xx)
    print(xx)
    print(result)
# PASSED             [100%]
# [1, 5, 3, 9, 7, 13, 11, 17, 15, 21, 19, 25, 23, 29, 27, 33, 31]
# [5.0, 5.857142857142857, 7.285714285714286, 7.0, 9.285714285714286, 10.714285714285714, 13.285714285714286,
#  14.714285714285714, 17.285714285714285, 18.714285714285715, 21.285714285714285, 22.714285714285715, 25.571428571428573,
#  27.0, 27.571428571428573, 28.142857142857142, 30.428571428571427]

def test_repetitious_moving_average_smoothing():
    x = Ystl().pet
    stl = STL(x)
    result1 = stl.moving_average_smoothing(41, x)
    result2 = stl.moving_average_smoothing(51, result1)
    result3 = stl.moving_average_smoothing(61, result2)
    pet_mas = pd.DataFrame({"pet": x, "result1": result1, "result2": result2, "result3": result3})
    pet_mas.index.name = "time"
    # file_name = r"D:\minio\waterism\datasets-origin\camels\camels_ystl\pet_moving_average_smoothing.csv"
    file_name = r"/mnt/d/minio/waterism/datasets-origin/camels/camels_ystl/pet_moving_average_smoothing.csv"
    pet_mas.to_csv(file_name, sep=" ")
    print(pet_mas)
# PASSED [100%]
# time  pet   result1   result2   result3
# 0     1.20  0.936585  0.978288  0.956109
# 1     1.30  0.939024  0.976997  0.955493
# 2     0.90  0.965854  0.972238  0.955219
# 3     0.55  1.006098  0.966308  0.955174
# 4     0.85  1.056098  0.961549  0.955298
# ...    ...       ...       ...       ...
# 5835  0.65  0.746341  0.757604  0.828124
# 5836  0.55  0.750000  0.751961  0.823865
# 5837  0.55  0.762195  0.747035  0.819445
# 5838  0.50  0.774390  0.743424  0.814950
# 5839  0.60  0.790244  0.740555  0.810459
#
# [5840 rows x 4 columns]

def test_weight_least_squares():
    x = Ystl().pet
    stl = STL(x)
    xx = [1, 2, 3, 4, 5]
    y = x[:5]
    y_ = stl.weight_least_squares_fit(xx, y, degree=2)
    print(y_)
    # PASSED[100 %]
    # 0.7283553118882566

def test_sample_loess():
    x = Ystl().pet
    stl = STL(x)
    y = [1, 5, 3, 7, 11, 9, 13, 17, 15, 19, 23, 21, 25, 29, 27, 31, 35, 33]  # 18
    result = stl.loess(7, y)
    print(y)
    print(result)
# PASSED                         [100%]
# [1, 5, 3, 7, 11, 9, 13, 17, 15, 19, 23, 21, 25, 29, 27, 31, 35, 33]
# [1.360129590021107, 3.2375224121135506, 5.201212543814867, 6.999999999999991, 8.861362741236697, 11.13863725876328,
# 12.999999999999984, 14.86136274123669, 17.138637258763275, 18.999999999999982, 20.861362741236686, 23.138637258763268,
# 24.999999999999975, 26.861362741236682, 29.138637258763257, 30.97743212943223, 32.65893534046176, 34.41033858673253]

def test_loess_subseries():
    x = Ystl().pet
    stl = STL(x)
    y = [1.2, 1.2, 0.5, 0.55, 1.2, 1.2, 0.5, 0.55, 1.2, 1.2, 0.5, 0.55, 1.2, 1.2, 0.5, 0.55]  # 18
    width = 15
    result = stl.loess(width, y)
    print("width = {}".format(width))
    print(y)
    print(result)
# width = 7
# PASSED                      [100%]
# [1.2, 1.2, 0.5, 0.55, 1.2, 1.2, 0.5, 0.55, 1.2, 1.2, 0.5, 0.55, 1.2, 1.2, 0.5, 0.55]
# [1.1171822571654677, 1.0022386742789637, 0.9092975581073439, 0.8339015068633021, 0.8932738173384088,
# 0.8904599361078279, 0.8323647396904573, 0.8339015068633021, 0.8932738173384088, 0.8904599361078279,
# 0.8323647396904573, 0.8339015068633021, 0.8932738173384088, 0.816049551484761, 0.7307655094915988, 0.6073610180542387]
# width = 13
# PASSED                      [100%]
# [1.2, 1.2, 0.5, 0.55, 1.2, 1.2, 0.5, 0.55, 1.2, 1.2, 0.5, 0.55, 1.2, 1.2, 0.5, 0.55]
# [0.9989823558152048, 0.9821281673224069, 0.9620592946659765, 0.9666575766223443, 0.9552633730078289,
# 0.8689770915187841, 0.8669454934464629, 0.8667012266500779, 0.8579785244574571, 0.8583747554460013,
# 0.8555111385537292, 0.8321474407007147, 0.8061637120257298, 0.7808825674768443, 0.755341587764194, 0.7269348455122501]
# PASSED                      [100%]
# width = 15
# [1.2, 1.2, 0.5, 0.55, 1.2, 1.2, 0.5, 0.55, 1.2, 1.2, 0.5, 0.55, 1.2, 1.2, 0.5, 0.55]
# [0.9864734751599387, 0.9754733442651808, 0.9607055611880029, 0.9699433193146715, 0.9630583361957221,
# 0.9359962557994859, 0.8620713293075262, 0.8579959965523511, 0.8673482403600385, 0.8626995180300019,
# 0.8449054684661481, 0.8240669246878335, 0.802758564984388, 0.7820964437960396, 0.7614263384564299, 0.7391728782521003]

def test_loess():
    x = Ystl().pet
    stl = STL(x)
    xx = x[:200]
    result = stl.loess(37, xx)
    print(xx)
    print(result)
# PASSED                                [100%]
# [1.2, 1.3, 0.9, 0.55, 0.85, 1.15, 0.9, 0.85, 0.7, 0.7, 0.8, 0.95, 1.05, 0.75, 0.6, 0.55, 1.1, 1.75, 1.3, 0.8, 1.05,
# 1.15, 1.25, 1.85, 1.8, 1.0, 0.75, 0.45, 0.35, 0.95, 1.05, 0.8, 1.1, 1.0, 0.7, 0.9, 0.9, 1.15, 1.0, 0.5, 0.65, 0.75,
# 0.95, 1.25, 0.85, 0.4, 0.35, 0.5, 0.9, 0.75, 0.35, 0.9, 0.9, 0.75, 1.3, 1.55, 1.55, 1.25, 1.0, 1.15, 0.9, 0.7, 1.15,
# 1.4, 1.35, 1.3, 1.75, 1.55, 1.15, 1.7, 1.2, 0.4, 0.5, 0.45, 1.05, 1.95, 2.1, 1.4, 1.0, 1.9, 2.2, 1.55, 1.4, 1.75,
# 1.65, 0.8, 0.75, 0.8, 0.9, 1.65, 1.2, 0.7, 1.7, 1.85, 1.4, 1.55, 1.45, 1.15, 0.9, 0.7, 1.25, 2.05, 1.9, 1.45, 0.95,
# 0.85, 1.5, 1.95, 1.55, 1.2, 1.6, 1.55, 1.25, 2.1, 2.65, 2.7, 1.55, 0.25, 0.8, 1.6, 1.0, 0.6, 2.2, 3.45, 3.65, 3.2,
# 2.85, 3.85, 2.65, 2.35, 4.15, 3.85, 3.75, 2.75, 1.9, 2.7, 3.65, 3.55, 2.35, 1.55, 1.3, 1.15, 1.3, 2.1, 3.05, 3.85,
# 3.1, 2.2, 2.4, 2.45, 3.3, 2.9, 2.25, 3.5, 4.0, 2.55, 1.05, 2.2, 3.95, 4.35, 3.8, 2.55, 1.8, 2.45, 3.55, 2.85, 2.2,
# 2.1, 1.75, 1.05, 1.05, 2.95, 3.85, 2.1, 1.25, 2.05, 3.15, 4.1, 3.05, 1.85, 1.8, 2.9, 4.35, 3.9, 3.25, 3.4, 2.55, 3.15,
# 4.55, 4.45, 3.4, 3.0, 3.5, 3.9, 4.35, 3.85, 2.3, 1.55, 1.5, 1.35]
# [0.8836166759929116, 0.8988489236971938, 0.9189820995426331, 0.9249137979022809, 0.9463732694446015,
# 0.9525613710182382, 0.9597237012511306, 0.9650465758349704, 0.9708773940823634, 0.9797656312934588,
# 0.9880120493184822, 0.9933506974391096, 0.9965707473103793, 0.9993763606267778, 1.0043367058024049,
# 1.0135921222858808, 1.025909550667806, 1.0005120910470313, 1.0102767400947137, 1.013231636389492, 1.0153745488731836,
# 1.0170514070985852, 1.0185928091929584, 1.0195970071570797, 1.0192688060276465, 1.0169016103145576,
# 1.0120973437215615, 1.0049153601179979, 0.9953737859335088, 0.98317866796033, 0.9680001504528399, 0.949927667627106,
# 0.9298706445051529, 0.9090720806296936, 0.8884357219629571, 0.868538489065472, 0.8498422752159247, 0.8332043185601815,
# 0.8200004726495321, 0.8114438813782006, 0.8081392923164837, 0.8097294384774981, 0.8149101798006924, 0.822360042095421,
# 0.8311699387061647, 0.8406764393007089, 0.8507767071751887, 0.8617693338418533, 0.8738516626572187,
# 0.8872958960253667, 0.9026748347149438, 0.9203845762593619, 0.940679671868085, 0.9638985958386638, 0.9897363738935011,
# 1.0169476420539696, 1.0437806379050223, 1.0686646124070514, 1.090936304461421, 1.1108873654908105, 1.1291487114724716,
# 1.145764455293569, 1.1603860024850023, 1.1735521461013678, 1.1865408876827996, 1.2002699100276961, 1.2150664822542312,
# 1.2310611306370296, 1.2482850019599223, 1.2661976257865606, 1.283603505288831, 1.2991338099807372, 1.3116801135071898,
# 1.3206353234861776, 1.3256010290381077, 1.3265386925724458, 1.324532507415039, 1.32129721209194, 1.3183991593378208,
# 1.317408834016908, 1.3195503509583477, 1.3249080813143874, 1.332419927845955, 1.3404317616497743, 1.3474145632548964,
# 1.3523005396340484, 1.3544674760521327, 1.3534248679003085, 1.3485348103100472, 1.3399848412930953,
# 1.3294305548804057, 1.3192292193728314, 1.3114298271806857, 1.3070643946661964, 1.3063247404312965,
# 1.3091586958645751, 1.3157012978211589, 1.3263374408866024, 1.3412067265911776, 1.3601921205155647,
# 1.3823842561091977, 1.4055227152708596, 1.4270481400796142, 1.4453255828547893, 1.4595365456794092,
# 1.4693765053794516, 1.4761055494241986, 1.4826444956924494, 1.4924128779007333, 1.5085370245381702,
# 1.5332291078061198, 1.5675245836621836, 1.6109259248063765, 1.6622653474966596, 1.7210240866523367,
# 2.9340911022088374]

def test_inner_loop():
    x = Ystl().pet
    stl = STL(x)
    trend = [0]*stl.length
    ni = 2
    trend_i, season_i = stl.inner_loop(x, trend)
    print(trend_i)
    print(season_i)
# [103.76759812692383, 102.20164037269491, 99.738328772511, 99.62958843004897, 98.2223414270767, 96.79183156477477, 96.53564693981045, 97.75621973426932,
# 99.36651326823953, 99.76874293165153, 98.26840677853927, 95.5474021764428, 92.89262740821509, 90.76571673210684, 88.66649746752341, 86.13674183015392,
# 83.2122625967781, 80.24603476363518, 77.55473379197005, 75.16664415298915, 72.9937418115444, 71.4692646445855, 71.16668204417813, 71.94585155934128,
# 73.23464587263436, 74.33493364446744, 74.97696990580846, 77.69157673072425, 85.67355032146186, 97.9056209327276, 109.50081442747407, 115.65118651916113,
# 114.92302464599325, 110.21141633508216, 105.57688065472742, 102.973535785042, 103.73671137632715, 109.04560034616493]

def test_outer_loop():
    x = Ystl().pet
    stl = STL(x)
    trend, season, residuals = stl.outer_loop()
    pet_stl = pd.DataFrame({"pet": x, "trend": trend, "season": season, "residuals": residuals})
    pet_stl.index.name = "time"
    # file_name = r"D:\minio\waterism\datasets-origin\camels\camels_ystl\pet_stl.csv"
    file_name = r"/mnt/d/minio/waterism/datasets-origin/camels/camels_ystl/pet_stl.csv"
    pet_stl.to_csv(file_name, sep=" ")
    print(pet_stl)
# PASSED                           [100%]
# time  pet     trend    season  residuals
# 0     1.20  1.733627 -0.533627        0.0
# 1     1.30  1.728555 -0.428555        0.0
# 2     0.90  1.723637 -0.823637        0.0
# 3     0.55  1.718873 -1.168873        0.0
# 4     0.85  1.714265 -0.864265        0.0
# ...    ...       ...       ...        ...
# 5835  0.65  1.354457 -0.704457        0.0
# 5836  0.55  1.354057 -0.804057        0.0
# 5837  0.55  1.353730 -0.803730        0.0
# 5838  0.50  1.353479 -0.853479        0.0
# 5839  0.60  1.353301 -0.753301        0.0
#
# [5840 rows x 4 columns]


def test_season_post_smoothing():
    x = Ystl().pet
    stl = STL(x)
    trend, season, residuals = stl.outer_loop()
    post_season = stl.season_post_smoothing(season)
    pet_post_season = pd.DataFrame({"pet": x, "trend": trend, "season": season, "residuals": residuals, "post_season": post_season})
    pet_post_season.index.name = "time"
    # file_name = r"D:\minio\waterism\datasets-origin\camels\camels_ystl\pet_post_season.csv"
    file_name = r"/mnt/d/minio/waterism/datasets-origin/camels/camels_ystl/pet_post_season.csv"
    pet_post_season.to_csv(file_name, sep=" ")
    print(pet_post_season)
# PASSED                [100%]
# time  pet     trend    season  residuals  post_season
# 0     1.20  1.733627 -0.533627        0.0    -0.533627
# 1     1.30  1.728555 -0.428555        0.0    -0.428555
# 2     0.90  1.723637 -0.823637        0.0    -0.982103
# 3     0.55  1.718873 -1.168873        0.0    -0.905982
# 4     0.85  1.714265 -0.864265        0.0    -0.733111
# ...    ...       ...       ...        ...          ...
# 5835  0.65  1.354457 -0.704457        0.0    -0.767987
# 5836  0.55  1.354057 -0.804057        0.0    -0.822173
# 5837  0.55  1.353730 -0.803730        0.0    -0.818743
# 5838  0.50  1.353479 -0.853479        0.0    -0.853479
# 5839  0.60  1.353301 -0.753301        0.0    -0.753301
#
# [5840 rows x 5 columns]


def test_decomposition():
    x = Ystl().pet
    stl = STL(x)
    trend, season, residuals, post_season, post_residuals = stl.decomposition()
    decomposition = pd.DataFrame(
        {"pet": x, "trend": trend, "season": season, "residuals": residuals, "post_season": post_season,
         "post_residuals": post_residuals})
    decomposition.index.name = "time"
    # file_name = r"D:\minio\waterism\datasets-origin\camels\camels_ystl\series_decomposition.csv"
    file_name = r"/mnt/d/minio/waterism/datasets-origin/camels/camels_ystl/series_decomposition.csv"
    decomposition.to_csv(file_name, sep=" ")
    print(decomposition)
# PASSED                        [100%]
# time   pet     trend    season  residuals  post_season  post_residuals
# 0      1.20  2.156395 -1.086812   0.130417    -1.191099        0.234704
# 1      1.30  2.153127 -1.085334   0.232208    -1.167534        0.314407
# 2      0.90  2.149884 -1.222679  -0.027205    -1.219176       -0.030708
# 3      0.55  2.146668 -1.359697  -0.236971    -1.256014       -0.340654
# 4      0.85  2.143481 -1.319349   0.025867    -1.212951       -0.080530
# ...     ...       ...       ...        ...          ...             ...
# 11675  0.65  1.764947 -1.443899   0.328952    -1.372693        0.257746
# 11676  0.55  1.768479 -1.442860   0.224380    -1.466157        0.247678
# 11677  0.55  1.771998 -1.462999   0.241002    -1.488468        0.266470
# 11678  0.50  1.775501 -1.498253   0.222752    -1.427140        0.151638
# 11679  0.60  1.778989 -1.371840   0.192852    -1.327310        0.148321
#
# [11680 rows x 6 columns]

def test_moving_average_smoothing_start_end():
    x = Ystl().pet
    stl = STL(x)
    xi = ["x0", "x1", "x2", "x3", "x4", "x5", "x6", "x7", "x8", "x9", "x10", "x11", "x12", "x13", "x14", "x15", "x16",
          "x17"]
    y = [1, 5, 3, 7, 11, 9, 13, 17, 15, 19, 23, 21, 25, 29, 27, 31, 35, 33]  # 18
    result = stl.moving_average_smoothing(7, xi, y)
    print(xi)
    print(y)
    print(result)
# PASSED   [100%]
# ['x3', 'x2', 'x1', 'x0', 'x1', 'x2', 'x3']
# ['x4', 'x3', 'x0', 'x1', 'x2', 'x3', 'x4']
# ['x5', 'x0', 'x1', 'x2', 'x3', 'x4', 'x5']
# ['x0', 'x1', 'x2', 'x3', 'x4', 'x5', 'x6']
# ['x1', 'x2', 'x3', 'x4', 'x5', 'x6', 'x7']
# ['x2', 'x3', 'x4', 'x5', 'x6', 'x7', 'x8']
# ['x3', 'x4', 'x5', 'x6', 'x7', 'x8', 'x9']
# ['x4', 'x5', 'x6', 'x7', 'x8', 'x9', 'x10']
# ['x5', 'x6', 'x7', 'x8', 'x9', 'x10', 'x11']
# ['x6', 'x7', 'x8', 'x9', 'x10', 'x11', 'x12']
# ['x7', 'x8', 'x9', 'x10', 'x11', 'x12', 'x13']
# ['x8', 'x9', 'x10', 'x11', 'x12', 'x13', 'x14']
# ['x9', 'x10', 'x11', 'x12', 'x13', 'x14', 'x15']
# ['x10', 'x11', 'x12', 'x13', 'x14', 'x15', 'x16']
# ['x11', 'x12', 'x13', 'x14', 'x15', 'x16', 'x17']
# ['x12', 'x13', 'x14', 'x15', 'x16', 'x17', 'x12']
# ['x13', 'x14', 'x15', 'x16', 'x17', 'x14', 'x13']
# ['x14', 'x15', 'x16', 'x17', 'x16', 'x15', 'x14']
# ['x0', 'x1', 'x2', 'x3', 'x4', 'x5', 'x6', 'x7', 'x8', 'x9', 'x10', 'x11', 'x12', 'x13', 'x14', 'x15', 'x16', 'x17']
# [1, 5, 3, 7, 11, 9, 13, 17, 15, 19, 23, 21, 25, 29, 27, 31, 35, 33]
# [4.428571428571429, 6.428571428571429, 6.428571428571429, 7.0, 9.285714285714286, 10.714285714285714, 13.0,
# 15.285714285714286, 16.714285714285715, 19.0, 21.285714285714285, 22.714285714285715, 25.0, 27.285714285714285,
# 28.714285714285715, 29.285714285714285, 30.142857142857142, 31.285714285714285]

def test_sample_loess():
    x = Ystl().pet
    stl = STL(x)
    xx = ["x0", "x1", "x2", "x3", "x4", "x5", "x6", "x7", "x8", "x9", "x10", "x11", "x12", "x13", "x14", "x15", "x16",
          "x17"]
    y = [1, 5, 3, 7, 11, 9, 13, 17, 15, 19, 23, 21, 25, 29, 27, 31, 35, 33]  # 18
    result = stl.loess(7, xx, y)
    print(xx)
    print(y)
    print(result)
# PASSED                         [100%]
# ['x3', 'x2', 'x1', 'x0', 'x1', 'x2', 'x3']
# ['x4', 'x3', 'x0', 'x1', 'x2', 'x3', 'x4']
# ['x5', 'x0', 'x1', 'x2', 'x3', 'x4', 'x5']
# ['x0', 'x1', 'x2', 'x3', 'x4', 'x5', 'x6']
# ['x1', 'x2', 'x3', 'x4', 'x5', 'x6', 'x7']
# ['x2', 'x3', 'x4', 'x5', 'x6', 'x7', 'x8']
# ['x3', 'x4', 'x5', 'x6', 'x7', 'x8', 'x9']
# ['x4', 'x5', 'x6', 'x7', 'x8', 'x9', 'x10']
# ['x5', 'x6', 'x7', 'x8', 'x9', 'x10', 'x11']
# ['x6', 'x7', 'x8', 'x9', 'x10', 'x11', 'x12']
# ['x7', 'x8', 'x9', 'x10', 'x11', 'x12', 'x13']
# ['x8', 'x9', 'x10', 'x11', 'x12', 'x13', 'x14']
# ['x9', 'x10', 'x11', 'x12', 'x13', 'x14', 'x15']
# ['x10', 'x11', 'x12', 'x13', 'x14', 'x15', 'x16']
# ['x11', 'x12', 'x13', 'x14', 'x15', 'x16', 'x17']
# ['x12', 'x13', 'x14', 'x15', 'x16', 'x17', 'x12']
# ['x13', 'x14', 'x15', 'x16', 'x17', 'x14', 'x13']
# ['x14', 'x15', 'x16', 'x17', 'x16', 'x15', 'x14']
# ['x0', 'x1', 'x2', 'x3', 'x4', 'x5', 'x6', 'x7', 'x8', 'x9', 'x10', 'x11', 'x12', 'x13', 'x14', 'x15', 'x16', 'x17']
# [1, 5, 3, 7, 11, 9, 13, 17, 15, 19, 23, 21, 25, 29, 27, 31, 35, 33]
# [3.4513004536635856, 3.8619024696220405, 5.138637258763287, 6.999999999999991, 8.861362741236697, 11.13863725876328,
# 12.999999999999984, 14.86136274123669, 17.138637258763275, 18.999999999999982, 20.861362741236686, 23.138637258763268,
# 24.999999999999975, 26.861362741236682, 29.138637258763257, 30.99999999999997, 31.86082301285134, 33.625326389800556]


def test_negative():
    x = Ystl().pet
    stl = STL(x)
    xx = [1, 5, 3, 7, 11, 9, 13, 17, 15, 19, 23, 21, 25, 29, 27, 31, 35, 33]
    result = stl._negative(xx)
    print(xx)
    print(result)
# PASSED                             [100%]
# [1, 5, 3, 7, 11, 9, 13, 17, 15, 19, 23, 21, 25, 29, 27, 31, 35, 33]
# [-1, -5, -3, -7, -11, -9, -13, -17, -15, -19, -23, -21, -25, -29, -27, -31, -35, -33]

def test_decomposition_streamflow():
    x = Ystl().streamflow
    stl = STL(x)
    trend, season, residuals, post_season, post_residuals = stl.decomposition()
    decomposition = pd.DataFrame(
        {"pet": x, "trend": trend, "season": season, "residuals": residuals, "post_season": post_season,
         "post_residuals": post_residuals})
    decomposition.index.name = "time"
    # file_name = r"D:\minio\waterism\datasets-origin\camels\camels_ystl\series_decomposition.csv"
    file_name = r"/mnt/d/minio/waterism/datasets-origin/camels/camels_ystl/series_decomposition.csv"
    decomposition.to_csv(file_name, sep=" ")
    print(decomposition)
# PASSED             [100%]
# time   pet       trend      season  residuals  post_season  post_residuals
# 0      167.6  318.601656 -239.431983  88.430327  -248.257325       97.255669
# 1      165.0  319.680010 -240.100241  85.420231  -242.269446       87.589435
# 2      160.6  320.762285 -240.847365  80.685080  -238.719000       78.556715
# 3      158.0  321.848072 -241.129072  77.281000  -238.083354       74.235281
# 4      158.0  322.936940 -235.300234  70.363294  -238.171508       73.234569
# ...      ...         ...         ...        ...          ...             ...
# 11675   75.7  417.704512 -255.427477 -86.577036  -256.079079      -85.925433
# 11676   74.0  415.817652 -253.929831 -87.887821  -255.818388      -85.999264
# 11677   71.2  413.912535 -254.490554 -88.221981  -256.062001      -86.650534
# 11678   71.1  411.990530 -256.348772 -84.541758  -254.235105      -86.655425
# 11679   68.0  410.053033 -256.998704 -85.054329  -249.742646      -92.310387
#
# [11680 rows x 6 columns]

def test_decomposition_prcp():
    x = Ystl().prcp
    stl = STL(x)
    trend, season, residuals, post_season, post_residuals = stl.decomposition()
    decomposition = pd.DataFrame(
        {"pet": x, "trend": trend, "season": season, "residuals": residuals, "post_season": post_season,
         "post_residuals": post_residuals})
    decomposition.index.name = "time"
    # file_name = r"D:\minio\waterism\datasets-origin\camels\camels_ystl\series_decomposition.csv"
    file_name = r"/mnt/d/minio/waterism/datasets-origin/camels/camels_ystl/series_decomposition.csv"
    decomposition.to_csv(file_name, sep=" ")
    print(decomposition)
# PASSED                   [100%]
# time   pet     trend    season  residuals  post_season  post_residuals
# 0      0.0  3.207341 -3.299541   0.092199    -3.168793       -0.038548
# 1      0.0  3.216307 -3.279715   0.063408    -3.077734       -0.138573
# 2      0.0  3.225302 -2.612596  -0.612707    -2.941555       -0.283747
# 3      0.0  3.234323 -2.867324  -0.366999    -2.914983       -0.319340
# 4      0.0  3.243365 -2.921127  -0.322238    -2.972998       -0.270367
# ...    ...       ...       ...        ...          ...             ...
# 11675  0.0  3.941500 -2.643090  -1.298410    -2.722671       -1.218829
# 11676  0.0  3.929213 -3.140227  -0.788987    -2.848158       -1.081055
# 11677  0.0  3.916848 -3.288694  -0.628154    -3.030611       -0.886237
# 11678  0.0  3.904413 -2.647311  -1.257102    -3.172870       -0.731543
# 11679  0.0  3.891918 -3.353523  -0.538395    -3.197138       -0.694780
#
# [11680 rows x 6 columns]






def test_rank():
    x = [1.2, 1.2, 0.5, 0.55, 1.2, 1.2, 0.5, 0.55, 1.2, 1.2, 0.5, 0.55, 1.2, 1.2, 0.5, 0.55]  # 16
    mi = MutualInformation(x)
    xx, incident, counts, frequency = mi.rank()
    print("x")
    print(x)
    print("xx")
    print(xx)
    print("incident")
    print(incident)
    print("counts")
    print(counts)
    print("frequency")
    print(frequency)
# PASSED                                 [100%]
# x
# [1.2, 1.2, 0.5, 0.55, 1.2, 1.2, 0.5, 0.55, 1.2, 1.2, 0.5, 0.55, 1.2, 1.2, 0.5, 0.55]
# xx
# [0.5  0.5  0.5  0.5  0.55 0.55 0.55 0.55 1.2  1.2  1.2  1.2  1.2  1.2  1.2  1.2 ]
# incident
# [0.5  0.55 1.2 ]
# counts
# [4 4 8]
# frequency
# [0.25 0.25 0.5 ]

def test_probability():
    x = [1.2, 1.2, 0.5, 0.55, 1.2, 1.2, 0.5, 0.55, 1.2, 1.2, 0.5, 0.55, 1.2, 1.2, 0.5, 0.55]  # 16
    mi = MutualInformation(x)
    px = mi.probability(x)
    print(px)
# PASSED                 [100%]
# [0.25 0.25 0.5 ]

def test_marginal_probability_():
    # ystl = Ystl()
    # prcp = ystl.prcp
    # pet = ystl.pet
    prcp = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.07, 0.22, 0.0, 0.0, 0.04, 0.0, 0.0, 0.0, 1.15, 0.0, 0.0, 0.04, 0.04, 0.0,
            0.07, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.81, 1.41, 4.34, 1.89]
    pet = [1.2, 1.3, 0.9, 0.55, 0.85, 1.15, 0.9, 0.85, 0.7, 0.7, 0.8, 0.95, 1.05, 0.75, 0.6, 0.55, 1.1, 1.75, 1.3, 0.8,
           1.05, 1.15, 1.25, 1.85, 1.8, 1.0, 0.75, 0.45, 0.35, 0.95, 1.05]
    # prcp = [0, 0, 0, 0, 0, 0, 0.07, 0.22, 0, 0]
    # pet = [1.2, 1.2, 0.9, 0.55, 0.85, 1.15, 0.9, 0.85, 0.7, 0.7]
    mi = MutualInformation(prcp, pet)
    prcp_incident, prcp_counts, prcp_frequency = mi.rank(prcp)
    pet_incident, pet_counts, pet_frequency = mi.rank(pet)
    print("prcp")
    print(prcp)
    print("prcp_incident")
    print(prcp_incident)
    print("prcp_counts")
    print(prcp_counts)
    print("prcp_frequency")
    print(prcp_frequency)
    print("pet")
    print(pet)
    print("pet_incident")
    print(pet_incident)
    print("pet_counts")
    print(pet_counts)
    print("pet_frequency")
    print(pet_frequency)
# PASSED                [100%]
# prcp
# [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.07, 0.22, 0.0, 0.0, 0.04, 0.0, 0.0, 0.0, 1.15, 0.0, 0.0, 0.04, 0.04, 0.0, 0.07, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.81, 1.41, 4.34, 1.89]
# prcp_incident
# [0.   0.04 0.07 0.22 0.81 1.15 1.41 1.89 4.34]
# prcp_counts
# [20  3  2  1  1  1  1  1  1]
# prcp_frequency
# [0.64516129 0.09677419 0.06451613 0.03225806 0.03225806 0.03225806
#  0.03225806 0.03225806 0.03225806]
# pet
# [1.2, 1.3, 0.9, 0.55, 0.85, 1.15, 0.9, 0.85, 0.7, 0.7, 0.8, 0.95, 1.05, 0.75, 0.6, 0.55, 1.1, 1.75, 1.3, 0.8, 1.05, 1.15, 1.25, 1.85, 1.8, 1.0, 0.75, 0.45, 0.35, 0.95, 1.05]
# pet_incident
# [0.35 0.45 0.55 0.6  0.7  0.75 0.8  0.85 0.9  0.95 1.   1.05 1.1  1.15
#  1.2  1.25 1.3  1.75 1.8  1.85]
# pet_counts
# [1 1 2 1 2 2 2 2 2 2 1 3 1 2 1 1 2 1 1 1]
# pet_frequency
# [0.03225806 0.03225806 0.06451613 0.03225806 0.06451613 0.06451613
#  0.06451613 0.06451613 0.06451613 0.06451613 0.03225806 0.09677419
#  0.03225806 0.06451613 0.03225806 0.03225806 0.06451613 0.03225806
#  0.03225806 0.03225806]

# PASSED                [100%]
# prcp
# [0, 0, 0, 0, 0, 0, 0.07, 0.22, 0, 0]
# prcp_incident
# [0.   0.07 0.22]
# prcp_counts
# [8 1 1]
# prcp_frequency
# [0.8 0.1 0.1]
# pet
# [1.2, 1.2, 0.9, 0.55, 0.85, 1.15, 0.9, 0.85, 0.7, 0.7]
# pet_incident
# [0.55 0.7  0.85 0.9  1.15 1.2 ]
# pet_counts
# [1 2 2 2 1 2]
# pet_frequency
# [0.1 0.2 0.2 0.2 0.1 0.2]


def test_joint_probability():
    # prcp = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.07, 0.22, 0.0, 0.0, 0.04, 0.0, 0.0, 0.0, 1.15, 0.0, 0.0, 0.04, 0.04, 0.0,
    #         0.07, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.81, 1.41, 4.34, 1.89]
    # pet = [1.2, 1.3, 0.9, 0.55, 0.85, 1.15, 0.9, 0.85, 0.7, 0.7, 0.8, 0.95, 1.05, 0.75, 0.6, 0.55, 1.1, 1.75, 1.3, 0.8,
    #        1.05, 1.15, 1.25, 1.85, 1.8, 1.0, 0.75, 0.45, 0.35, 0.95, 1.05]
    prcp = [0, 0, 0, 0, 0, 0, 0.07, 0.22, 0, 0]
    pet = [1.2, 1.2, 0.9, 0.55, 0.85, 1.15, 0.9, 0.85, 0.7, 0.7]
    mi = MutualInformation(prcp, pet)
    # xy, incident, counts, frequency = mi.joint_probability(prcp, pet)
    distribution_low = mi.joint_probability(prcp, pet)
    # print("prcp")
    # print(prcp)
    # print("pet")
    # print(pet)
    # print("xy")
    # print(xy)
    # print("incident")
    # print(incident)
    # print("counts")
    # print(counts)
    # print("frequency")
    # print(frequency)
    print("distribution_low")
    print(distribution_low)
# PASSED                    [100%]
# xy
# [[0.   1.2 ]
#  [0.   1.2 ]
#  [0.   0.9 ]
#  [0.   0.55]
#  [0.   0.85]
#  [0.   1.15]
#  [0.07 0.9 ]
#  [0.22 0.85]
#  [0.   0.7 ]
#  [0.   0.7 ]]
# incident
# [[0.   0.55]
#  [0.   0.7 ]
#  [0.   0.85]
#  [0.   0.9 ]
#  [0.   1.15]
#  [0.   1.2 ]
#  [0.07 0.9 ]
#  [0.22 0.85]]
# counts
# [1 2 1 1 1 2 1 1]
# frequency
# [0.1 0.2 0.1 0.1 0.1 0.2 0.1 0.1]
# PASSED                    [100%]
# distribution_low
# [[0.   0.55 0.1 ]
#  [0.   0.7  0.2 ]
#  [0.   0.85 0.1 ]
#  [0.   0.9  0.1 ]
#  [0.   1.15 0.1 ]
#  [0.   1.2  0.2 ]
#  [0.07 0.9  0.1 ]
#  [0.22 0.85 0.1 ]]
# PASSED                    [100%]
# prcp
# [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.07, 0.22, 0.0, 0.0, 0.04, 0.0, 0.0, 0.0, 1.15, 0.0, 0.0, 0.04, 0.04, 0.0, 0.07, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.81, 1.41, 4.34, 1.89]
# pet
# [1.2, 1.3, 0.9, 0.55, 0.85, 1.15, 0.9, 0.85, 0.7, 0.7, 0.8, 0.95, 1.05, 0.75, 0.6, 0.55, 1.1, 1.75, 1.3, 0.8, 1.05, 1.15, 1.25, 1.85, 1.8, 1.0, 0.75, 0.45, 0.35, 0.95, 1.05]
# xy
# [[0.   1.2 ]
#  [0.   1.3 ]
#  [0.   0.9 ]
#  [0.   0.55]
#  [0.   0.85]
#  [0.   1.15]
#  [0.07 0.9 ]
#  [0.22 0.85]
#  [0.   0.7 ]
#  [0.   0.7 ]
#  [0.04 0.8 ]
#  [0.   0.95]
#  [0.   1.05]
#  [0.   0.75]
#  [1.15 0.6 ]
#  [0.   0.55]
#  [0.   1.1 ]
#  [0.04 1.75]
#  [0.04 1.3 ]
#  [0.   0.8 ]
#  [0.07 1.05]
#  [0.   1.15]
#  [0.   1.25]
#  [0.   1.85]
#  [0.   1.8 ]
#  [0.   1.  ]
#  [0.   0.75]
#  [0.81 0.45]
#  [1.41 0.35]
#  [4.34 0.95]
#  [1.89 1.05]]
# incident
# [[0.   0.55]
#  [0.   0.7 ]
#  [0.   0.75]
#  [0.   0.8 ]
#  [0.   0.85]
#  [0.   0.9 ]
#  [0.   0.95]
#  [0.   1.  ]
#  [0.   1.05]
#  [0.   1.1 ]
#  [0.   1.15]
#  [0.   1.2 ]
#  [0.   1.25]
#  [0.   1.3 ]
#  [0.   1.8 ]
#  [0.   1.85]
#  [0.04 0.8 ]
#  [0.04 1.3 ]
#  [0.04 1.75]
#  [0.07 0.9 ]
#  [0.07 1.05]
#  [0.22 0.85]
#  [0.81 0.45]
#  [1.15 0.6 ]
#  [1.41 0.35]
#  [1.89 1.05]
#  [4.34 0.95]]
# counts
# [2 2 2 1 1 1 1 1 1 1 2 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1 1]
# frequency
# [0.06451613 0.06451613 0.06451613 0.03225806 0.03225806 0.03225806
#  0.03225806 0.03225806 0.03225806 0.03225806 0.06451613 0.03225806
#  0.03225806 0.03225806 0.03225806 0.03225806 0.03225806 0.03225806
#  0.03225806 0.03225806 0.03225806 0.03225806 0.03225806 0.03225806
#  0.03225806 0.03225806 0.03225806]


def test_marginal_probability():
    prcp = [0, 0, 0, 0, 0, 0, 0.07, 0.22, 0, 0]
    pet = [1.2, 1.2, 0.9, 0.55, 0.85, 1.15, 0.9, 0.85, 0.7, 0.7]
    # prcp = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.07, 0.22, 0.0, 0.0, 0.04, 0.0, 0.0, 0.0, 1.15, 0.0, 0.0, 0.04, 0.04, 0.0,
    #         0.07, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.81, 1.41, 4.34, 1.89]
    # pet = [1.2, 1.3, 0.9, 0.55, 0.85, 1.15, 0.9, 0.85, 0.7, 0.7, 0.8, 0.95, 1.05, 0.75, 0.6, 0.55, 1.1, 1.75, 1.3, 0.8,
    #        1.05, 1.15, 1.25, 1.85, 1.8, 1.0, 0.75, 0.45, 0.35, 0.95, 1.05]
    mi = MutualInformation(prcp, pet)
    distribution_low = mi.marginal_probability(pet)
    # print("px")
    # print(px)
    # print("py")
    # print(py)
    # print("pxy")
    # print(pxy)
    # print("mi_prcp_pet")
    # print(mi_prcp_pet)
    print("distribution_low")
    print(distribution_low)
# PASSED                 [100%]
# distribution_low
# [[0.55 0.1 ]
#  [0.7  0.2 ]
#  [0.85 0.2 ]
#  [0.9  0.2 ]
#  [1.15 0.1 ]
#  [1.2  0.2 ]]


def test_mutual_information():
    ystl = Ystl()
    prcp = ystl.prcp
    pet = ystl.pet
    # prcp = [0, 0, 0, 0, 0, 0, 0.07, 0.22, 0, 0]
    # pet = [1.2, 1.2, 0.9, 0.55, 0.85, 1.15, 0.9, 0.85, 0.7, 0.7]
    # prcp = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.07, 0.22, 0.0, 0.0, 0.04, 0.0, 0.0, 0.0, 1.15, 0.0, 0.0, 0.04, 0.04, 0.0,
    #         0.07, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.81, 1.41, 4.34, 1.89]
    # pet = [1.2, 1.3, 0.9, 0.55, 0.85, 1.15, 0.9, 0.85, 0.7, 0.7, 0.8, 0.95, 1.05, 0.75, 0.6, 0.55, 1.1, 1.75, 1.3, 0.8,
    #        1.05, 1.15, 1.25, 1.85, 1.8, 1.0, 0.75, 0.45, 0.35, 0.95, 1.05]
    mi = MutualInformation(prcp, pet)
    dl_x, dl_y, dl_xy, mi = mi.mutual_information()
    print("prcp")
    print(len(prcp))
    print("pet")
    print(len(pet))
    print("dl_x")
    print(dl_x.shape[0])
    print("dl_y")
    print(dl_y.shape[0])
    print("dl_xy")
    print(dl_xy.shape[0])
    print("mi")
    print(mi)
# PASSED                   [100%]
# dl_x
# [[0.   0.8 ]
#  [0.07 0.1 ]
#  [0.22 0.1 ]]
# dl_y
# [[0.55 0.1 ]
#  [0.7  0.2 ]
#  [0.85 0.2 ]
#  [0.9  0.2 ]
#  [1.15 0.1 ]
#  [1.2  0.2 ]]
# dl_xy
# [[0.   0.55 0.1 ]
#  [0.   0.7  0.2 ]
#  [0.   0.85 0.1 ]
#  [0.   0.9  0.1 ]
#  [0.   1.15 0.1 ]
#  [0.   1.2  0.2 ]
#  [0.07 0.9  0.1 ]
#  [0.22 0.85 0.1 ]]
# mi
# [0.36177299]
# PASSED                   [100%]dl_x
# [[0.         0.64516129]
#  [0.04       0.09677419]
#  [0.07       0.06451613]
#  [0.22       0.03225806]
#  [0.81       0.03225806]
#  [1.15       0.03225806]
#  [1.41       0.03225806]
#  [1.89       0.03225806]
#  [4.34       0.03225806]]
# dl_y
# [[0.35       0.03225806]
#  [0.45       0.03225806]
#  [0.55       0.06451613]
#  [0.6        0.03225806]
#  [0.7        0.06451613]
#  [0.75       0.06451613]
#  [0.8        0.06451613]
#  [0.85       0.06451613]
#  [0.9        0.06451613]
#  [0.95       0.06451613]
#  [1.         0.03225806]
#  [1.05       0.09677419]
#  [1.1        0.03225806]
#  [1.15       0.06451613]
#  [1.2        0.03225806]
#  [1.25       0.03225806]
#  [1.3        0.06451613]
#  [1.75       0.03225806]
#  [1.8        0.03225806]
#  [1.85       0.03225806]]
# dl_xy
# [[0.         0.55       0.06451613]
#  [0.         0.7        0.06451613]
#  [0.         0.75       0.06451613]
#  [0.         0.8        0.03225806]
#  [0.         0.85       0.03225806]
#  [0.         0.9        0.03225806]
#  [0.         0.95       0.03225806]
#  [0.         1.         0.03225806]
#  [0.         1.05       0.03225806]
#  [0.         1.1        0.03225806]
#  [0.         1.15       0.06451613]
#  [0.         1.2        0.03225806]
#  [0.         1.25       0.03225806]
#  [0.         1.3        0.03225806]
#  [0.         1.8        0.03225806]
#  [0.         1.85       0.03225806]
#  [0.04       0.8        0.03225806]
#  [0.04       1.3        0.03225806]
#  [0.04       1.75       0.03225806]
#  [0.07       0.9        0.03225806]
#  [0.07       1.05       0.03225806]
#  [0.22       0.85       0.03225806]
#  [0.81       0.45       0.03225806]
#  [1.15       0.6        0.03225806]
#  [1.41       0.35       0.03225806]
#  [1.89       1.05       0.03225806]
#  [4.34       0.95       0.03225806]]
# mi
# [1.02030703]


def test_mutual_information_p_e():
    ystl = Ystl()
    prcp = ystl.prcp
    pet = ystl.pet
    mi = MutualInformation(prcp, pet)
    dl_x, dl_y, dl_xy, mi = mi.mutual_information()
    print("prcp")
    print(len(prcp))
    print("pet")
    print(len(pet))
    print("dl_x")
    print(dl_x.shape)
    print("dl_y")
    print(dl_y.shape)
    print("dl_xy")
    print(dl_xy.shape)
    print("mi")
    print(mi)
# PASSED               [100%]
# prcp
# 11680
# pet
# 11680
# dl_x
# (381, 2)
# dl_y
# (128, 2)
# dl_xy
# (894, 3)
# mi
# [1.76120705]

def test_mutual_information_p_q():
    ystl = Ystl()
    prcp = ystl.prcp
    streamflow = ystl.streamflow
    mi = MutualInformation(prcp, streamflow)
    dl_x, dl_y, dl_xy, mi = mi.mutual_information()
    print("prcp")
    print(len(prcp))
    print("streamflow")
    print(len(streamflow))
    print("dl_x")
    print(dl_x.shape)
    print("dl_y")
    print(dl_y.shape)
    print("dl_xy")
    print(dl_xy.shape)
    print("mi")
    print(mi)
# PASSED                  [100%]
# prcp
# 11680
# streamflow
# 11680
# dl_x
# (381, 2)
# dl_y
# (3244, 2)
# dl_xy
# (4714, 3)
# mi
# [3.1592755]

def test_mutual_information_e_q():
    ystl = Ystl()
    pet = ystl.pet
    streamflow = ystl.streamflow
    mi = MutualInformation(pet, streamflow)
    dl_x, dl_y, dl_xy, mi = mi.mutual_information()
    print("pet")
    print(len(pet))
    print("streamflow")
    print(len(streamflow))
    print("dl_x")
    print(dl_x.shape)
    print("dl_y")
    print(dl_y.shape)
    print("dl_xy")
    print(dl_xy.shape)
    print("mi")
    print(mi)
# PASSED               [100%]
# pet
# 11680
# streamflow
# 11680
# dl_x
# (128, 2)
# dl_y
# (3244, 2)
# dl_xy
# (5439, 3)
# mi
# [3.68717948]





def date_string2number(date_str):
    str_list = date_str.split("-")
    date_num = [int(s) for s in str_list]
    return date_num

def marge_time_range(
    t_range_train: list = None,
    t_range_valid: list = None,
    t_range_test: list = None,
):
    """marge time range"""
    t_range_list = []
    if t_range_train is not None:
        t_range_list.append(t_range_train)
    if t_range_valid is not None:
        t_range_list.append(t_range_valid)
    if t_range_test is not None:
        t_range_list.append(t_range_test)
    t_n = len(t_range_list)
    for i in range(t_n-1):
        if t_range_list[i][1] != t_range_list[i+1][0]:
            raise ValueError("t_range_list and t_range_list must be equal")
    time_range = [t_range_list[0][0], t_range_list[-1][-1]]

    return time_range


def test_date_string2number():
    date = ["1980-01-01", "1981-01-01"]
    date_num = date_string2number(date[0])
    print(date_num)
# [1980, 1, 1]

def test_marge_time_range():
    t_range_train = ["1980-10-01", "2012-10-01"]
    t_range_valid = ["2012-10-01", "2013-10-01"]
    t_range_test = ["2013-10-01", "2014-10-01"]
    t_range_str, t_range_num = marge_time_range(
        t_range_train, t_range_valid, t_range_test
    )
    print(t_range_str)
    print(t_range_num)
# ['1980-10-01', '2014-10-01']
# [[1980, 10, 1], [2014, 10, 1]]

def test_stl_decomposition():
    data_cfgs = {
        "source_cfgs": {
            "source_name": "camels_us",
            # "source_path": "camels\camels_us",
            "source_path": "camels/camels_us",
        },
        "object_ids": [
            "01013500",
            "01022500",
            # # "01030500",
            # # "01031500",
            # # "01047000",
            # # "01052500",
            # # "01054200",
            # # "01055000",
            # # "01057000",
            # # "01073000",
            # # "01078000",
            # # "01118300",
            # # "01121000",
            # # "01123000",
            # # "01134500",
            # # "01137500",
            # # "01139000",
            # # "01139800",
            # # "01142500",
            # # "01144000",
            # "02092500",  # 02108000 -> 02092500
            # "02108000",
        ],  # Add this line with the actual object IDs
        "t_range_train": ["1981-10-01", "2012-09-30"],
        # Add this line with the actual start and end dates for training.
        # "t_range_valid": None,
        "t_range_valid": ["2012-10-01", "2013-09-30"],
        # Add this line with the actual start and end dates for validation.
        # "t_range_test": None,
        "t_range_test": ["2013-10-01", "2014-09-30"],
        # Add this line with the actual start and end dates for testing.
        "relevant_cols": [
            # List the relevant column names here.
            "prcp",
            "PET",
            # ... other relevant columns ...
        ],
        "target_cols": [
            # List the target column names here.
            "streamflow",
            # ... other target columns ...
        ],
        "constant_cols": [
            # "elev_mean",
            # "slope_mean",
            # "area_gages2",
            # "frac_forest",
            # "lai_max",
            # "lai_diff",
            # "dom_land_cover_frac",
            # "dom_land_cover",
            # "root_depth_50",
            # "soil_depth_statsgo",
            # "soil_porosity",
            # "soil_conductivity",
            # "max_water_content",
            # "geol_1st_class",
            # "geol_2nd_class",
            # "geol_porostiy",
            # "geol_permeability",
        ],
    }
    decompose = Decomposition(data_cfgs)
    # y_decomposed, x_origin, y_origin, c_origin = decompose.stl_decomposition()
    # train_data, valid_data, test_data = decompose.split_period()
    train_data, valid_data, test_data, time_step_mi = decompose.stl_decomposition()
    # print("y_decomposed")
    # print(y_decomposed)
    # print("x_origin")
    # print(x_origin)
    # print("y_origin")
    # print(y_origin)
    # print("c_origin")
    # print(c_origin)
    print("train_data")
    print(train_data)
    print("valid_data")
    print(valid_data)
    print("test_data")
    print(test_data)
    print("time_step_mi")
    print(time_step_mi)

# train_data
# [<xarray.Dataset> Size: 453kB
# Dimensions:  (basin: 2, time: 11315)
# Coordinates:
#   * basin    (basin) <U8 64B '01013500' '01022500'
#   * time     (time) datetime64[ns] 91kB 1981-10-01 1981-10-02 ... 2012-09-30
# Data variables:
#     prcp     (basin, time) float64 181kB ...
#     PET      (basin, time) float64 181kB ..., <xarray.Dataset> Size: 272kB
# Dimensions:     (basin: 2, time: 11315)
# Coordinates:
#   * basin       (basin) <U8 64B '01013500' '01022500'
#   * time        (time) datetime64[ns] 91kB 1981-10-01 1981-10-02 ... 2012-09-30
# Data variables:
#     streamflow  (basin, time) float64 181kB 802.0 795.0 857.0 ... 157.0 504.0, None, <xarray.Dataset> Size: 634kB
# Dimensions:    (basin: 2, time: 11315)
# Coordinates:
#   * basin      (basin) <U8 64B '01013500' '01022500'
#   * time       (time) datetime64[ns] 91kB 1981-10-01 1981-10-02 ... 2012-09-30
# Data variables:
#     trend      (basin, time) float64 181kB 1.755e+03 1.756e+03 ... 603.6 603.5
#     season     (basin, time) float64 181kB -888.6 -859.6 ... -167.0 -109.5
#     residuals  (basin, time) float64 181kB -64.76 -101.5 -63.07 ... -279.6 9.99]
# valid_data
# [<xarray.Dataset> Size: 15kB
# Dimensions:  (basin: 2, time: 365)
# Coordinates:
#   * basin    (basin) <U8 64B '01013500' '01022500'
#   * time     (time) datetime64[ns] 3kB 2012-10-01 2012-10-02 ... 2013-09-30
# Data variables:
#     prcp     (basin, time) float64 6kB ...
#     PET      (basin, time) float64 6kB ..., <xarray.Dataset> Size: 9kB
# Dimensions:     (basin: 2, time: 365)
# Coordinates:
#   * basin       (basin) <U8 64B '01013500' '01022500'
#   * time        (time) datetime64[ns] 3kB 2012-10-01 2012-10-02 ... 2013-09-30
# Data variables:
#     streamflow  (basin, time) float64 6kB 356.0 327.0 304.0 ... 254.0 235.0, None, <xarray.Dataset> Size: 21kB
# Dimensions:    (basin: 2, time: 365)
# Coordinates:
#   * basin      (basin) <U8 64B '01013500' '01022500'
#   * time       (time) datetime64[ns] 3kB 2012-10-01 2012-10-02 ... 2013-09-30
# Data variables:
#     trend      (basin, time) float64 6kB 1.265e+03 1.266e+03 ... 590.5 590.5
#     season     (basin, time) float64 6kB -974.2 -915.8 -866.0 ... -180.7 -105.7
#     residuals  (basin, time) float64 6kB 65.51 -22.88 -96.69 ... -155.8 -249.8]
# test_data
# [<xarray.Dataset> Size: 15kB
# Dimensions:  (basin: 2, time: 365)
# Coordinates:
#   * basin    (basin) <U8 64B '01013500' '01022500'
#   * time     (time) datetime64[ns] 3kB 2013-10-01 2013-10-02 ... 2014-09-30
# Data variables:
#     prcp     (basin, time) float64 6kB ...
#     PET      (basin, time) float64 6kB ..., <xarray.Dataset> Size: 9kB
# Dimensions:     (basin: 2, time: 365)
# Coordinates:
#   * basin       (basin) <U8 64B '01013500' '01022500'
#   * time        (time) datetime64[ns] 3kB 2013-10-01 2013-10-02 ... 2014-09-30
# Data variables:
#     streamflow  (basin, time) float64 6kB 710.0 691.0 662.0 ... 48.0 46.0 46.0, None, <xarray.Dataset> Size: 21kB
# Dimensions:    (basin: 2, time: 365)
# Coordinates:
#   * basin      (basin) <U8 64B '01013500' '01022500'
#   * time       (time) datetime64[ns] 3kB 2013-10-01 2013-10-02 ... 2014-09-30
# Data variables:
#     trend      (basin, time) float64 6kB 1.5e+03 1.498e+03 ... 474.9 474.2
#     season     (basin, time) float64 6kB -979.3 -929.3 -882.3 ... -181.8 -106.7
#     residuals  (basin, time) float64 6kB 189.4 122.1 47.9 ... -247.1 -321.5]
# time_step_mi
# 8


def test_mutual_information_q():
    ystl = Ystl()
    streamflow = ystl.streamflow[:366]
    n = 30
    mi_ = [0]*n
    for i in range(1, n):
        x = streamflow[i:]
        y = streamflow[:-i]
        mi = MutualInformation(x, y)
        dl_x, dl_y, dl_xy, mi_i = mi.mutual_information()
        mi_[i] = float(mi_i)
        # print("----------i = " + str(i) + ":----------")
        # print("len(x) = " + str(len(x)))
        # print("len(y) = " + str(len(y)))
        # print("dl_x.shape = ")
        # print(dl_x.shape)
        # print("dl_y.shape = ")
        # print(dl_y.shape)
        # print("dl_xy.shape = ")
        # print(dl_xy.shape)
        # print("mi_i = ")
        # print(mi_i)
    print("mi_ = ")
    print(mi_)
# mi_ =
# [0, 5.633958429349199, 5.63192183686367, 5.62844013674035, 5.640264980453122, 5.640642536183852, 5.625626613452512, 5.622119406652182, 5.618600387296957,
# 5.618952655398646, 5.615420685576694, 5.61187672998804, 5.6083207094105205, 5.6047525438511085, 5.610535325450293, 5.614868415688737, 5.607351883366596,
# 5.603772653174086, 5.60018108640981, 5.600572184760152, 5.600973872836158, 5.59334977781463, 5.589719708158951, 5.58607694707914, 5.586474900312144,
# 5.586883762305412, 5.579148981820009, 5.579555972254977, 5.577420707128609, 5.5778425169913906]

def test_time_step():
    ystl = Ystl()
    streamflow = ystl.streamflow[:366]
    n = 15
    mi = MutualInformation()
    n_timestep, mi_ = mi.time_step(streamflow, n)
    print(n_timestep)
    print(mi_)
# time_step = 4
# [0, 5.633958429349199, 5.63192183686367, 5.62844013674035, 5.640264980453122, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
