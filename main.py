import datetime

import pandas as pd
import shapely
import streamlit as st
import streamlit_folium as st_folium
from PIL import Image
from folium.plugins import DualMap
import folium
import building_and_road_growth as map_utils
import osmnx as ox


# st.set_page_config(layout="wide")
# if 'last_object_clicked' not in st.session_state:
#     st.session_state['last_object_clicked'] = None
def rerun_count():
    if 'rerun_count' not in st.session_state:
        st.session_state.rerun_count = 0
    else:
        st.session_state.rerun_count += 1

    st.info(f'rerun count : {st.session_state.rerun_count}')


API_KEY = "pk.eyJ1IjoibHNkYTNtMG5zIiwiYSI6ImNreHBzb2FlbzAyZHMycG1wd2lvaXF3dDcifQ.otSnSJfhxkSjeXRTGGTE3w"

colors_rgb = [
    [65, 182, 196],
    [127, 205, 187],
    [199, 233, 180],
    [237, 248, 177],
    [255, 255, 204],
    [255, 237, 160],
    [254, 217, 118],
    [254, 178, 76],
    [253, 141, 60],
    [252, 78, 42],
    [227, 26, 28],
    [189, 0, 38],
    [128, 0, 38],
]


@st.cache_data()
def get_city_polygon_from_osm(city_name):
    try:
        data = ox.geocode_to_gdf(f'{city_name}', which_result=None)
    except ValueError:
        data = ox.geocode_to_gdf(f'{city_name}', which_result=1)
    except:
        st.info(f'Location {city_name} not found')
    return data


def get_maps_by_lat_lng_buffer(lat, lng, zoom, radius):
    polygon, area_tuple = get_polygon_and_area(lat, lng, zoom, radius)
    satellite_map, building_map = map_utils.generate_map1(lat, lng, zoom, polygon)
    building_area, road_area, total_area = area_tuple
    area = dict(building_area=building_area, road_area=road_area, total_area=total_area)
    area_km2 = {}
    for key, value in area.items():
        area_km2[f'{key} km^2'] = round(value / 1000_000, 3)
    # st.success(f'Map Extracted {datetime.datetime.now()}')
    return satellite_map, building_map, area_km2


def get_maps_by_polygon(city_name, zoom):
    # st.info(f'Extracting {city_name} polygons')
    building_area, road_area, total_area, lat, lng, polygon, name = _get_maps_by_polygon(city_name, zoom)
    satellite_map, building_map = map_utils.generate_map1(lat, lng, zoom, polygon, tooltip=name)
    area = dict(building_area=building_area, road_area=road_area, total_area=total_area)
    area_km2 = {}
    for key, value in area.items():
        area_km2[f'{key} km^2'] = round(value / 1000_000, 3)
    # st.success(f'Map Extracted {datetime.datetime.now()}')
    # st.success(f'Extracted {city_name} polygons')

    return satellite_map, building_map, area_km2, lat, lng


@st.cache_data(ttl=None, persist='disk')
def _get_maps_by_polygon(city_name, zoom):
    data = get_city_polygons(city_name)
    geom = data['geometry']
    lat = data['lat']
    lon = data['lon']
    name = data['display_name']
    if isinstance(geom, str):
        polygon = shapely.from_wkt(geom)
    elif isinstance(geom, shapely.Point):
        lng, lat = geom.coords[0]
        polygon, _ = map_utils.generate_polygon(lat, lng, 500)
        st.info(f'Point Extracted from OSM.Polygon Generated')
    else:
        polygon = geom
        st.info(f'Polygon Extracted from OSM')
    building_area, road_area, total_area = map_utils.building_road_area_for_polygon(polygon, zoom, num_workers=100)
    return building_area, road_area, total_area, lat, lon, polygon, name


def get_city_polygons(city_name):
    df = get_city_polygon_from_osm(city_name)
    if df is None:
        st.info(f'location {city_name} not found')
    data = df.to_dict(orient='records')[0]
    return data


def get_cities_with_available_polygons():
    df = pd.read_csv("data/top_8_cities.csv")
    return df


@st.cache_data
def get_polygon_and_area(lat, lng, zoom, radius, polygon=None):
    polygon, area_meters = map_utils.generate_polygon(lat, lng, radius)
    building_area, road_area, total_area = map_utils.building_road_area_for_polygon(polygon, zoom, num_workers=100)
    return polygon, tuple([building_area, road_area, total_area])


def main_loop():
    # rerun_count()
    # st.write("----")
    _, col1, col2, col3 = st.sidebar.columns((1, 5, 1, 4))
    with col1:
        st.title("Location Analysis")
    with col3:
        st.text("\n")
        # col11, col22 = st.columns((1, 3))
        # with col22:
        st.image("favicon.png", width=60)

    st.sidebar.write("----")
    select_by = st.sidebar.radio(
        "Select Area By",
        ("city", "coordinates",),
        index=1,
        horizontal=True,
    )

    if select_by == "city":
        city = st.sidebar.text_input("City Name", value='bengaluru', placeholder='city..',
                                     autocomplete='bengaluru, hapur, aizawl')

        # city_ = st.sidebar.multiselect("City Name",
        #                               options=['bengaluru', 'hapur', 'aizawl'])
        zoom_level = '18'
        if city.strip():
            map1, map2, area, lat, lng = get_maps_by_polygon(city.strip(), int(zoom_level))
            area = pd.DataFrame([area])
            add_map_to_layout(map1, map2, lat, lng, zoom_level, area)


    elif select_by == 'coordinates':
        coordinates = st.sidebar.text_input('Enter Coordinates', help='Comma seperated Lat long',
                                            value='12.918877105665517,77.64305106225419')
        radius = st.sidebar.text_input('Enter Radius', help='radius', value='500')
        zoom_level = '18'  # st.sidebar.text_input('Zoom Level', help='radius in meters', value='18')
        st.sidebar.write("----")
        if coordinates and radius and zoom_level:
            lat, lng = list(map(float, coordinates.split(',')))
            zoom = float(zoom_level)
            radius = float(radius)  # meters
            # f'{coordinates} | {radius} (m) | {zoom_level}z'
            map1, map2, area = get_maps_by_lat_lng_buffer(lat, lng, zoom, radius)
            area = pd.DataFrame([area])
            add_map_to_layout(map1, map2, lat, lng, zoom_level, area)


def add_map_to_layout(map1, map2, lat, lng, zoom_level, area_info):
    m = DualMap(location=(lat, lng), layout='horizontal', zoom_start=zoom_level, tiles=None)
    m.m1 = map1
    m.m2 = map2
    # testmarker = folium.Marker([12.921045075125779, 77.64285922050476])
    # last_clicked = st.session_state.get('last_clicked', None)
    # # last_clicked
    # if last_clicked is not None:
    #     # st.session_state['last_clicked'] = last_clicked
    # #     marker = folium.Marker([last_object_clicked['lat'], last_object_clicked['lng']])
    #     testmarker.add_to(m)
    f = folium.Figure()
    m.add_to(f)
    a = st_folium.st_folium(f, width=700, key='2')
    area_info
    # last_clicked_ = a['last_clicked'].copy()
    # if last_clicked_:
    #     last_clicked_=last_clicked_.copy()
    # st.session_state['last_clicked'] = last_clicked_


def _remove_top_padding_():
    st.markdown("""
        <style>
               .css-18e3th9 {
                    padding-top: 0rem;
                    padding-bottom: 10rem;
                    padding-left: 5rem;
                    padding-right: 5rem;
                }
               .css-1d391kg {
                    padding-top: 3.5rem;
                    padding-right: 1rem;
                    padding-bottom: 3.5rem;
                    padding-left: 1rem;
                }
        </style>
        """, unsafe_allow_html=True)


def _max_width_():
    max_width_str = f"max-width: 1400px;"
    st.markdown(
        f"""
    <style>
    .reportview-container .main .block-container{{
        {max_width_str}
    }}
    </style>    
    """,
        unsafe_allow_html=True,
    )


def _dual_map_with_():
    max_width_str = f"max-width: 1400px;"
    st.markdown(
        '''
    <style>
        iframe#map_div,iframe#map_div2
         {
            height: 700px;
            width: 100%;
            position: absolute;
            outline: none;
         }
    </style>
    ''',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    favicon = Image.open("favicon.png")
    st.set_page_config(
        page_title="Spatic | Hyperlocal Analysis",
        page_icon=favicon,
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'Get Help': None,
            'Report a bug': None,
            'About': "https://www.gospatic.com/#team",
        }
    )
    _remove_top_padding_()
    _max_width_()
    _dual_map_with_()
    main_loop()
