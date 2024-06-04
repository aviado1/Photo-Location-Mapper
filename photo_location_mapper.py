
The generated map will be saved as 'photo_map.html' in the current directory.
"""

import os
import warnings
import base64
from urllib.parse import quote
from PIL import Image, ExifTags
from PIL.ExifTags import TAGS, GPSTAGS
import folium
from folium.plugins import MarkerCluster
from tqdm import tqdm
from io import BytesIO

# Suppress the DecompressionBombWarning
warnings.simplefilter('ignore', Image.DecompressionBombWarning)

THUMBNAIL_SIZE = (150, 150)  # Size of the thumbnail for the preview

def get_exif_data(image):
 exif_data = {}
 info = image._getexif()
 if info:
     for tag, value in info.items():
         tag_name = TAGS.get(tag, tag)
         exif_data[tag_name] = value
 return exif_data

def get_geotagging(exif_data):
 if 'GPSInfo' not in exif_data:
     return None

 geotagging = {}
 for key in exif_data['GPSInfo'].keys():
     decode = GPSTAGS.get(key, key)
     geotagging[decode] = exif_data['GPSInfo'][key]

 return geotagging

def get_coordinates(geotags):
 def convert_to_degrees(value):
     d = float(value[0])
     m = float(value[1])
     s = float(value[2])
     return d + (m / 60.0) + (s / 3600.0)

 lat = None
 lon = None

 if 'GPSLatitude' in geotags and 'GPSLongitude' in geotags and 'GPSLatitudeRef' in geotags and 'GPSLongitudeRef' in geotags:
     lat = convert_to_degrees(geotags['GPSLatitude'])
     if geotags['GPSLatitudeRef'] != 'N':
         lat = -lat

     lon = convert_to_degrees(geotags['GPSLongitude'])
     if geotags['GPSLongitudeRef'] != 'E':
         lon = -lon

 return lat, lon

def correct_image_orientation(image):
 try:
     for orientation in ExifTags.TAGS.keys():
         if ExifTags.TAGS[orientation] == 'Orientation':
             break

     exif = dict(image._getexif().items())

     if exif[orientation] == 3:
         image = image.rotate(180, expand=True)
     elif exif[orientation] == 6:
         image = image.rotate(270, expand=True)
     elif exif[orientation] == 8:
         image = image.rotate(90, expand=True)

 except (AttributeError, KeyError, IndexError):
     pass

 return image

def encode_thumbnail_image(file_path):
 image = Image.open(file_path)
 image = correct_image_orientation(image)
 image.thumbnail(THUMBNAIL_SIZE)  # Create smaller thumbnail
 buffer = BytesIO()
 image.save(buffer, format="JPEG")
 encoded_image = base64.b64encode(buffer.getvalue()).decode()
 return encoded_image

def scan_folder(folder_path):
 locations = []
 total_files = sum([len(files) for r, d, files in os.walk(folder_path)])
 with tqdm(total=total_files, desc="Scanning photos", unit="file", bar_format="{l_bar}{bar}{r_bar}", colour="green") as pbar:
     for root, dirs, files in os.walk(folder_path):
         for file in files:
             if file.lower().endswith(('jpg', 'jpeg')):
                 file_path = os.path.join(root, file)
                 try:
                     image = Image.open(file_path)
                     exif_data = get_exif_data(image)
                     geotags = get_geotagging(exif_data)
                     if geotags:
                         coordinates = get_coordinates(geotags)
                         if coordinates[0] and coordinates[1]:
                             encoded_thumbnail_image = encode_thumbnail_image(file_path)
                             locations.append((file_path, coordinates, encoded_thumbnail_image))
                 except Exception as e:
                     pass
                 pbar.update(1)
 return locations

def create_map(locations):
 if not locations:
     print("No locations found to plot on map.")
     return None

 avg_lat = sum([loc[1][0] for loc in locations]) / len(locations)
 avg_lon = sum([loc[1][1] for loc in locations]) / len(locations)

 map_ = folium.Map(location=[avg_lat, avg_lon], zoom_start=10)
 marker_cluster = MarkerCluster().add_to(map_)

 for file_path, coordinates, encoded_thumbnail_image in locations:
     file_url = f"file:///{quote(file_path)}"
     html = f'''
     <div style="text-align: center;">
         <a href="#" onclick="navigator.clipboard.writeText('{file_url}'); alert('Copied URL to clipboard: {file_url}'); return false;">
             <img src="data:image/jpeg;base64,{encoded_thumbnail_image}" alt="Image" style="max-width: 100%; height: auto;"/>
         </a>
         <div style="background: rgba(255, 255, 255, 0.8); color: black; padding: 5px;">{file_path}</div>
     </div>
     '''
     iframe = folium.IFrame(html, width=170, height=170)  # Adjusted dimensions to fit smaller thumbnails
     popup = folium.Popup(iframe, max_width=170)
     marker = folium.Marker(
         location=[coordinates[0], coordinates[1]],
         popup=popup
     )
     marker.add_to(marker_cluster)

 return map_

if __name__ == "__main__":
 # Set the folder path containing geotagged images
 folder_path = r"Path\to\your\geotagged\images\folder"

 locations = scan_folder(folder_path)
 if locations:
     print(f"Found {len(locations)} geotagged images.")
     for location in locations:
         print(f"Image: {location[0]}, Coordinates: {location[1]}")
     photo_map = create_map(locations)
     if photo_map:
         photo_map.save('photo_map.html')
         print("\033[92mMap has been created and saved as 'photo_map.html'.\033[0m")
     else:
         print("Map creation failed.")
 else:
     print("No geotagged images found.")
