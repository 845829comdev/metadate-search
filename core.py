import exifread
from PIL import Image, ExifTags, ImageCms
import piexif
import os
import logging
import json
import io
import requests
import reverse_geocoder as rg
from geopy.geocoders import Nominatim
import hashlib
import folium
import webbrowser
import tempfile
from datetime import datetime

logger = logging.getLogger(__name__)

class OSINTEnhancer:
    """OSINT-усилитель для метаданных"""
    
    def __init__(self):
        # Небольшой таймаут чтобы сетевые запросы не висели бесконечно
        self.geolocator = Nominatim(user_agent="metadate_joot", timeout=5)
    
    def enhance_metadata(self, metadata, image_path):
        """Добавляет OSINT-данные к метаданным"""
        enhanced = metadata.copy()
        
        try:
            # 1. GPS анализ и геолокация
            enhanced.update(self._gps_osint_analysis(metadata))
            
            # 2. Анализ камеры и устройства
            enhanced.update(self._camera_osint_analysis(metadata))
            
            # 3. Временной анализ
            enhanced.update(self._time_analysis(metadata))
            
            # 4. Хеши и идентификаторы
            enhanced.update(self._forensic_analysis(image_path))
            
            # 5. Сетевой анализ (если есть ссылки)
            enhanced.update(self._network_analysis(metadata))
            
            # 6. Создание карты
            map_path = self._create_osm_map(metadata)
            if map_path:
                enhanced["OSINT_Map_File"] = map_path
                
        except Exception as e:
            enhanced["OSINT_Error"] = str(e)
            
        return enhanced
    
    def _gps_osint_analysis(self, metadata):
        """Углубленный GPS анализ для OSINT"""
        gps_data = {}
        
        try:
            # Ищем координаты в разных форматах
            coords = self._extract_coordinates(metadata)
            
            if coords:
                lat, lon = coords
                gps_data["OSINT_Coordinates"] = f"{lat:.6f}, {lon:.6f}"
                
                # 1. Обратная геокодировка - получаем адрес
                location = self.geolocator.reverse(f"{lat}, {lon}", language='en')
                if location:
                    address = location.raw.get('address', {})
                    gps_data["OSINT_Country"] = address.get('country', 'Unknown')
                    gps_data["OSINT_Country_Code"] = address.get('country_code', 'Unknown')
                    gps_data["OSINT_State"] = address.get('state', 'Unknown')
                    gps_data["OSINT_City"] = address.get('city', address.get('town', 'Unknown'))
                    gps_data["OSINT_Postcode"] = address.get('postcode', 'Unknown')
                    gps_data["OSINT_Road"] = address.get('road', 'Unknown')
                    gps_data["OSINT_Full_Address"] = location.address
                
                # 2. Reverse geocoding через alternative service
                try:
                    results = rg.search((lat, lon))
                    if results:
                        result = results[0]
                        gps_data["OSINT_RG_Country"] = result.get('cc', 'Unknown')
                        gps_data["OSINT_RG_City"] = result.get('name', 'Unknown')
                        gps_data["OSINT_RG_Admin1"] = result.get('admin1', 'Unknown')
                        gps_data["OSINT_RG_Admin2"] = result.get('admin2', 'Unknown')
                except:
                    pass
                
                # 3. Ссылки на карты
                gps_data["OSINT_Google_Maps"] = f"https://maps.google.com/?q={lat},{lon}&z=17"
                gps_data["OSINT_OpenStreetMap"] = f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}&zoom=17"
                gps_data["OSINT_Bing_Maps"] = f"https://bing.com/maps/default.aspx?cp={lat}~{lon}&lvl=17"
                gps_data["OSINT_Yandex_Maps"] = f"https://yandex.ru/maps/?pt={lon},{lat}&z=17"
                gps_data["OSINT_What3Words"] = f"https://what3words.com///{self._coord_to_3words(lat, lon)}"
                
                # 4. Высота и временная зона (если есть)
                if 'GPS GPSAltitude' in str(metadata):
                    gps_data["OSINT_Altitude_Analysis"] = "Altitude data available"
                
                # 5. Анализ местности
                gps_data["OSINT_Location_Type"] = self._analyze_location_type(lat, lon)
                
        except Exception as e:
            gps_data["OSINT_GPS_Error"] = str(e)
            
        return gps_data
    
    def _camera_osint_analysis(self, metadata):
        """Анализ камеры и устройства для OSINT"""
        camera_data = {}
        
        try:
            # Собираем информацию о камере
            make = None
            model = None
            serial = None
            
            for key, value in metadata.items():
                key_lower = key.lower()
                if 'make' in key_lower and not make:
                    make = str(value)
                elif 'model' in key_lower and not model:
                    model = str(value)
                elif 'serial' in key_lower and not serial:
                    serial = str(value)
            
            if make:
                camera_data["OSINT_Camera_Make"] = make
            if model:
                camera_data["OSINT_Camera_Model"] = model
            if serial:
                camera_data["OSINT_Camera_Serial"] = serial
                camera_data["OSINT_Serial_Hash_MD5"] = hashlib.md5(serial.encode()).hexdigest()
                camera_data["OSINT_Serial_Hash_SHA1"] = hashlib.sha1(serial.encode()).hexdigest()
            
            # Анализ по комбинации производитель+модель
            if make and model:
                camera_data["OSINT_Device_Fingerprint"] = f"{make} {model}"
                camera_data["OSINT_Device_Search"] = f"https://www.google.com/search?q={make}+{model}+camera"
                
            # Анализ объектива
            lens_info = self._extract_lens_info(metadata)
            if lens_info:
                camera_data["OSINT_Lens_Info"] = lens_info
            
        except Exception as e:
            camera_data["OSINT_Camera_Error"] = str(e)
            
        return camera_data
    
    def _time_analysis(self, metadata):
        """Анализ временных меток для OSINT"""
        time_data = {}
        
        try:
            # Ищем все временные метки
            timestamps = []
            for key, value in metadata.items():
                if any(time_key in key.lower() for time_key in ['date', 'time']):
                    if '202' in str(value) or '201' in str(value):  # Фильтр для дат
                        timestamps.append((key, str(value)))
            
            if timestamps:
                time_data["OSINT_Timestamps_Found"] = len(timestamps)
                for i, (key, value) in enumerate(timestamps[:5]):  # Первые 5
                    time_data[f"OSINT_Time_{i+1}"] = f"{key}: {value}"
                
                # Анализ временных паттернов
                if len(timestamps) > 1:
                    time_data["OSINT_Time_Analysis"] = "Multiple timestamps - timeline available"
            
            # Анализ временной зоны
            for key, value in metadata.items():
                if 'timezone' in key.lower():
                    time_data["OSINT_Timezone"] = value
                    break
                    
        except Exception as e:
            time_data["OSINT_Time_Error"] = str(e)
            
        return time_data
    
    def _forensic_analysis(self, image_path):
        """Криминалистический анализ файла"""
        forensic_data = {}
        
        try:
            # Хеши файла
            with open(image_path, 'rb') as f:
                file_data = f.read()
                
            forensic_data["OSINT_MD5_Hash"] = hashlib.md5(file_data).hexdigest()
            forensic_data["OSINT_SHA1_Hash"] = hashlib.sha1(file_data).hexdigest()
            forensic_data["OSINT_SHA256_Hash"] = hashlib.sha256(file_data).hexdigest()
            
            # Размер и характеристики
            file_stats = os.stat(image_path)
            forensic_data["OSINT_File_Size_Bytes"] = file_stats.st_size
            forensic_data["OSINT_File_Created"] = datetime.fromtimestamp(file_stats.st_ctime).isoformat()
            forensic_data["OSINT_File_Modified"] = datetime.fromtimestamp(file_stats.st_mtime).isoformat()
            
            # Анализ имени файла
            filename = os.path.basename(image_path)
            forensic_data["OSINT_Filename_Analysis"] = filename
            if any(x in filename.lower() for x in ['img', 'dsc', 'photo', 'pic']):
                forensic_data["OSINT_Filename_Pattern"] = "Common camera naming pattern"
                
        except Exception as e:
            forensic_data["OSINT_Forensic_Error"] = str(e)
            
        return forensic_data
    
    def _network_analysis(self, metadata):
        """Анализ сетевых данных"""
        network_data = {}
        
        try:
            # Ищем URL, IP, email в метаданных
            for key, value in metadata.items():
                str_value = str(value)
                
                # Поиск URL
                if 'http' in str_value.lower():
                    network_data[f"OSINT_URL_In_{key}"] = str_value
                
                # Поиск email-подобных строк
                if '@' in str_value and '.' in str_value:
                    network_data[f"OSINT_Email_Like_In_{key}"] = str_value
                    
        except Exception as e:
            network_data["OSINT_Network_Error"] = str(e)
            
        return network_data
    
    def _create_osm_map(self, metadata):
        """Создает OSM карту с локацией"""
        try:
            coords = self._extract_coordinates(metadata)
            if not coords:
                return None
                
            lat, lon = coords
            
            # Создаем карту
            m = folium.Map(location=[lat, lon], zoom_start=15)
            
            # Добавляем маркер
            # Добавляем простой маркер (избегаем зависимостей на FA icons)
            folium.Marker(
                [lat, lon],
                popup="Photo Location",
                tooltip="GPS from EXIF",
            ).add_to(m)
            
            # Сохраняем во временный файл
            temp_dir = tempfile.gettempdir()
            map_path = os.path.join(temp_dir, f"metadate_map_{hashlib.md5(f'{lat}{lon}'.encode()).hexdigest()}.html")
            m.save(map_path)
            
            return map_path
            
        except Exception as e:
            return None
    
    def _extract_coordinates(self, metadata):
        """Извлекает координаты из метаданных"""
        try:
            lat, lon = None, None
            
            # Ищем в разных форматах
            for key, value in metadata.items():
                key_lower = key.lower()
                if 'gps' in key_lower and 'decimal' in key_lower:
                    if 'latitude' in key_lower:
                        try:
                            lat = float(value)
                        except:
                            pass
                    elif 'longitude' in key_lower:
                        try:
                            lon = float(value)
                        except:
                            pass
            
            # Альтернативный поиск
            if lat is None or lon is None:
                for key, value in metadata.items():
                    if 'coordinates' in key.lower():
                        try:
                            coords = str(value).split(',')
                            if len(coords) == 2:
                                lat = float(coords[0].strip())
                                lon = float(coords[1].strip())
                        except:
                            continue
            
            if lat is not None and lon is not None:
                return (lat, lon)
            return None
            
        except:
            return None
    
    def _coord_to_3words(self, lat, lon):
        """Простая эмуляция what3words (для демо)"""
        return f"demo.words.{hashlib.md5(f'{lat}{lon}'.encode()).hexdigest()[:8]}"
    
    def _analyze_location_type(self, lat, lon):
        """Анализ типа местности по координатам"""
        try:
            location = self.geolocator.reverse(f"{lat}, {lon}")
            if location:
                address = location.raw.get('address', {})
                
                # Определяем тип местности
                if address.get('aeroway'):
                    return "Airport/Transport"
                elif address.get('tourism'):
                    return "Tourist location"
                elif address.get('historic'):
                    return "Historic site"
                elif address.get('leisure'):
                    return "Leisure area"
                elif address.get('waterway'):
                    return "Water area"
                else:
                    return "Urban/Residential"
                    
        except:
            return "Unknown"
    
    def _extract_lens_info(self, metadata):
        """Извлекает информацию об объективе"""
        lens_data = []
        
        for key, value in metadata.items():
            if 'lens' in key.lower():
                lens_data.append(f"{key}: {value}")
            elif 'focal' in key.lower() and 'length' in key.lower():
                lens_data.append(f"Focal: {value}")
            elif 'aperture' in key.lower():
                lens_data.append(f"Aperture: {value}")
                
        return ' | '.join(lens_data) if lens_data else None

class UltraMetadataExtractor:
    """УЛЬТРА-экстрактор - вытягивает ВСЁ что возможно из фото"""
    
    def extract_metadata(self, image_path):
        """Извлекаем АБСОЛЮТНО ВСЕ метаданные"""
        try:
            metadata = {}
            
            logger.info(f"Начинаем глубокий анализ: {image_path}")
            
            # 1. Базовая информация о файле
            metadata.update(self._get_file_info(image_path))
            
            # 2. Глубокий EXIF через exifread
            metadata.update(self._deep_exifread(image_path))
            
            # 3. Расширенный PIL EXIF
            metadata.update(self._extended_pil_exif(image_path))
            
            # 4. Низкоуровневый piexif анализ
            metadata.update(self._low_level_piexif(image_path))
            
            # 5. GPS данные с максимальной детализацией
            metadata.update(self._detailed_gps(image_path))
            
            # 6. MakerNotes от производителей камер
            metadata.update(self._extract_makernotes(image_path))
            
            # 7. Технические характеристики изображения
            metadata.update(self._image_technical_specs(image_path))
            
            # 8. Цветовые профили и метаданные
            metadata.update(self._color_analysis(image_path))
            
            # 9. XMP и IPTC данные если есть
            metadata.update(self._xmp_iptc_data(image_path))
            
            # 10. Специфичные данные для RAW форматов
            metadata.update(self._raw_specific_data(image_path))
            
            logger.info(f"Извлечено {len(metadata)} метаданных - РЕКОРД!")
            return metadata
            
        except Exception as e:
            logger.error(f"Критическая ошибка: {e}")
            return {"Error": f"Extraction failed: {str(e)}"}
    
    def extract_osint_metadata(self, image_path):
        """Извлекает метаданные с OSINT-усилением"""
        try:
            # Сначала получаем базовые метаданные
            basic_metadata = self.extract_metadata(image_path)
            
            # Затем усиливаем OSINT-данными
            osint_enhancer = OSINTEnhancer()
            enhanced_metadata = osint_enhancer.enhance_metadata(basic_metadata, image_path)
            
            logger.info(f"OSINT enhancement added {len(enhanced_metadata) - len(basic_metadata)} additional data points")
            return enhanced_metadata
            
        except Exception as e:
            logger.error(f"OSINT extraction failed: {e}")
            return self.extract_metadata(image_path)  # Fallback to basic
    
    def _get_file_info(self, image_path):
        """Базовая информация о файле"""
        info = {}
        try:
            stat = os.stat(image_path)
            info["File_Path"] = os.path.abspath(image_path)
            info["File_Name"] = os.path.basename(image_path)
            info["File_Size_Bytes"] = stat.st_size
            info["File_Size_MB"] = f"{stat.st_size / (1024*1024):.2f}"
            info["File_Created"] = datetime.fromtimestamp(stat.st_ctime).isoformat()
            info["File_Modified"] = datetime.fromtimestamp(stat.st_mtime).isoformat()
            info["File_Extension"] = os.path.splitext(image_path)[1].lower()
        except Exception as e:
            logger.warning(f"File info error: {e}")
        return info
    
    def _deep_exifread(self, image_path):
        """СУПЕР-глубокий анализ через exifread"""
        metadata = {}
        try:
            with open(image_path, 'rb') as f:
                # Включаем ВСЕ возможные детали
                tags = exifread.process_file(f, details=True, strict=True, debug=True)
                
                for tag, value in tags.items():
                    # Пропускаем только бинарные миниатюры
                    if tag in ['JPEGThumbnail', 'TIFFThumbnail']:
                        continue
                    
                    # Обрабатываем разные типы данных
                    processed_value = self._process_exif_value(value)
                    if processed_value and str(processed_value).strip():
                        metadata[f"EXIFDEEP_{tag}"] = processed_value
                        
        except Exception as e:
            logger.warning(f"Deep exifread: {e}")
        return metadata
    
    def _extended_pil_exif(self, image_path):
        """Расширенный EXIF через PIL"""
        metadata = {}
        try:
            with Image.open(image_path) as img:
                # Вся основная информация
                metadata["PIL_Format"] = str(img.format)
                metadata["PIL_Mode"] = str(img.mode)
                metadata["PIL_Size"] = f"{img.width}x{img.height}"
                metadata["PIL_Width"] = img.width
                metadata["PIL_Height"] = img.height
                metadata["PIL_Bands"] = str(img.getbands())
                
                # ВСЕ EXIF данные
                exif_data = img._getexif()
                if exif_data:
                    for tag_id, value in exif_data.items():
                        tag_name = ExifTags.TAGS.get(tag_id, tag_id)
                        
                        # Пропускаем совсем пустые
                        if value in [None, "", b'', 0]:
                            continue
                            
                        processed_value = self._process_exif_value(value)
                        if processed_value:
                            metadata[f"PILEXIF_{tag_name}"] = processed_value
                
                # Дополнительная информация PIL
                if hasattr(img, 'info'):
                    for key, value in img.info.items():
                        if key not in ['exif', 'icc_profile']:  # их обработаем отдельно
                            metadata[f"PILINFO_{key}"] = str(value)
                            
        except Exception as e:
            logger.warning(f"Extended PIL: {e}")
        return metadata
    
    def _low_level_piexif(self, image_path):
        """Низкоуровневый анализ через piexif"""
        metadata = {}
        try:
            exif_dict = piexif.load(image_path)
            
            # Анализируем ВСЕ IFD секции
            for ifd_name in ("0th", "Exif", "GPS", "1st", "Interop"):
                if ifd_name in exif_dict:
                    for tag, value in exif_dict[ifd_name].items():
                        try:
                            tag_name = piexif.TAGS[ifd_name][tag]["name"]
                            
                            # Пропускаем только полностью пустые
                            if value in [None, "", b'', 0, []]:
                                continue
                                
                            processed_value = self._process_exif_value(value)
                            if processed_value:
                                metadata[f"PIEXIF_{ifd_name}_{tag_name}"] = processed_value
                                
                        except Exception as e:
                            # Даже ошибки записываем
                            metadata[f"PIEXIF_ERROR_{ifd_name}_{tag}"] = f"Tag error: {e}"
                            
        except Exception as e:
            logger.warning(f"Low level piexif: {e}")
        return metadata
    
    def _detailed_gps(self, image_path):
        """Детальный GPS анализ"""
        metadata = {}
        try:
            with open(image_path, 'rb') as f:
                tags = exifread.process_file(f)
            
            # Собираем ВСЕ GPS теги
            gps_data = {}
            for tag, value in tags.items():
                if 'GPS' in tag:
                    gps_data[tag] = value
                    metadata[f"GPS_RAW_{tag}"] = str(value)
            
            if gps_data:
                metadata["GPS_Presence"] = "YES"
                
                # Подробный разбор координат
                try:
                    if 'GPS GPSLatitude' in gps_data and 'GPS GPSLongitude' in gps_data:
                        lat = self._convert_gps_coord(gps_data['GPS GPSLatitude'].values)
                        lon = self._convert_gps_coord(gps_data['GPS GPSLongitude'].values)
                        
                        # Учет направления
                        if 'GPS GPSLatitudeRef' in gps_data:
                            ref = str(gps_data['GPS GPSLatitudeRef']).upper()
                            metadata["GPS_Lat_Ref"] = ref
                            if ref == 'S':
                                lat = -lat
                                
                        if 'GPS GPSLongitudeRef' in gps_data:
                            ref = str(gps_data['GPS GPSLongitudeRef']).upper()
                            metadata["GPS_Lon_Ref"] = ref
                            if ref == 'W':
                                lon = -lon
                        
                        # Множество форматов координат
                        metadata["GPS_Latitude_Decimal"] = f"{lat:.8f}"
                        metadata["GPS_Longitude_Decimal"] = f"{lon:.8f}"
                        metadata["GPS_Coordinates"] = f"{lat:.6f}, {lon:.6f}"
                        metadata["GPS_Google_Maps"] = f"https://maps.google.com/?q={lat},{lon}"
                        metadata["GPS_OpenStreetMap"] = f"https://www.openstreetmap.org/?mlat={lat}&mlon={lon}"
                        
                        # DMS формат
                        metadata["GPS_Latitude_DMS"] = self._decimal_to_dms(lat, True)
                        metadata["GPS_Longitude_DMS"] = self._decimal_to_dms(lon, False)
                        
                except Exception as e:
                    metadata["GPS_Error"] = f"Coordinate processing: {e}"
                
                # Дополнительные GPS данные
                gps_mapping = {
                    'GPS GPSAltitude': 'Altitude',
                    'GPS GPSTimeStamp': 'TimeStamp', 
                    'GPS GPSDate': 'Date',
                    'GPS GPSProcessingMethod': 'ProcessingMethod',
                    'GPS GPSSpeed': 'Speed',
                    'GPS GPSTrack': 'Track',
                    'GPS GPSImgDirection': 'ImageDirection'
                }
                
                for gps_tag, friendly_name in gps_mapping.items():
                    if gps_tag in gps_data:
                        metadata[f"GPS_{friendly_name}"] = str(gps_data[gps_tag])
                    
        except Exception as e:
            logger.warning(f"Detailed GPS: {e}")
        return metadata
    
    def _extract_makernotes(self, image_path):
        """Извлечение MakerNotes - данных производителей"""
        metadata = {}
        try:
            with open(image_path, 'rb') as f:
                tags = exifread.process_file(f, details=True)
            
            # Ищем MakerNotes
            maker_tags = {}
            for tag, value in tags.items():
                if 'MakerNote' in tag or 'makernote' in tag.lower():
                    maker_tags[tag] = value
            
            if maker_tags:
                metadata["MakerNotes_Present"] = "YES"
                for tag, value in maker_tags.items():
                    processed = self._process_exif_value(value)
                    if processed:
                        metadata[f"MAKER_{tag}"] = processed
                        
                metadata["MakerNotes_Count"] = len(maker_tags)
            else:
                metadata["MakerNotes_Present"] = "NO"
                
        except Exception as e:
            logger.warning(f"MakerNotes: {e}")
        return metadata
    
    def _image_technical_specs(self, image_path):
        """Технические характеристики изображения"""
        metadata = {}
        try:
            with Image.open(image_path) as img:
                # Различные технические параметры
                metadata["Technical_Format"] = img.format
                metadata["Technical_Mode"] = img.mode
                metadata["Technical_Size"] = f"{img.width}x{img.height}"
                metadata["Technical_Width"] = img.width
                metadata["Technical_Height"] = img.height
                metadata["Technical_Aspect_Ratio"] = f"{img.width/img.height:.4f}"
                
                # Информация о цветовых каналах
                if hasattr(img, 'getbands'):
                    bands = img.getbands()
                    metadata["Technical_Color_Bands"] = str(bands)
                    metadata["Technical_Channels"] = len(bands)
                
                # Попытка получить битность
                try:
                    if img.mode in ['L', 'P']:
                        metadata["Technical_Bit_Depth"] = "8"
                    elif img.mode in ['I', 'F']:
                        metadata["Technical_Bit_Depth"] = "32"
                    elif img.mode == 'RGB':
                        metadata["Technical_Bit_Depth"] = "24"
                    elif img.mode == 'RGBA':
                        metadata["Technical_Bit_Depth"] = "32"
                except:
                    pass
                    
        except Exception as e:
            logger.warning(f"Technical specs: {e}")
        return metadata
    
    def _color_analysis(self, image_path):
        """Анализ цветовых профилей"""
        metadata = {}
        try:
            with Image.open(image_path) as img:
                # ICC профиль
                if 'icc_profile' in img.info:
                    icc_data = img.info['icc_profile']
                    metadata["Color_ICC_Present"] = "YES"
                    metadata["Color_ICC_Size_Bytes"] = len(icc_data)
                    
                    try:
                        icc_profile = ImageCms.ImageCmsProfile(io.BytesIO(icc_data))
                        metadata["Color_ICC_Description"] = ImageCms.getProfileDescription(icc_profile)
                        metadata["Color_ICC_Manufacturer"] = ImageCms.getProfileManufacturer(icc_profile)
                        metadata["Color_ICC_Model"] = ImageCms.getProfileModel(icc_profile)
                        metadata["Color_ICC_Copyright"] = ImageCms.getProfileCopyright(icc_profile)
                    except Exception as e:
                        metadata["Color_ICC_Error"] = f"Profile parsing: {e}"
                else:
                    metadata["Color_ICC_Present"] = "NO"
                    
        except Exception as e:
            logger.warning(f"Color analysis: {e}")
        return metadata
    
    def _xmp_iptc_data(self, image_path):
        """XMP и IPTC данные"""
        metadata = {}
        try:
            # Pillow не всегда раскрывает XMP/IPTC; поэтому читаем сырые байты
            with open(image_path, 'rb') as f:
                raw = f.read()

            # Поиск XMP блока
            xmp_start = raw.find(b'<x:xmpmeta')
            if xmp_start == -1:
                xmp_start = raw.find(b'<xpacket')

            if xmp_start != -1:
                # Попробуем извлечь до совпадения закрывающего тега или ограничим размер
                end_tag = raw.find(b'</x:xmpmeta>', xmp_start)
                if end_tag == -1:
                    end_tag = raw.find(b'</xpacket>', xmp_start)
                end_index = end_tag + 12 if end_tag != -1 else xmp_start + 20000
                xmp_raw = raw[xmp_start:end_index]
                try:
                    metadata['XMP_Raw'] = xmp_raw.decode('utf-8', errors='ignore')
                    metadata['XMP_Present'] = 'YES'
                except:
                    metadata['XMP_Raw'] = f'raw_bytes_{len(xmp_raw)}'
                    metadata['XMP_Present'] = 'YES'
            else:
                metadata['XMP_Present'] = 'NO'

            # Поиск IPTC (Photoshop IRB / IPTC headers)
            if b'Photoshop 3.0' in raw or b'IPTC' in raw or b'8BIM' in raw:
                metadata['IPTC_Present'] = 'YES'
                # Не парсим все IPTC, просто извлекаем небольшие фрагменты для анализа
                sample = raw[:4000]
                try:
                    metadata['IPTC_Sample'] = sample.decode('utf-8', errors='ignore')
                except:
                    metadata['IPTC_Sample'] = f'raw_bytes_{len(sample)}'
            else:
                metadata['IPTC_Present'] = 'NO'
                        
        except Exception as e:
            logger.warning(f"XMP IPTC: {e}")
        return metadata
    
    def _raw_specific_data(self, image_path):
        """Данные специфичные для RAW форматов"""
        metadata = {}
        file_ext = os.path.splitext(image_path)[1].lower()
        
        # Определяем RAW формат
        raw_formats = {
            '.cr2': 'Canon RAW',
            '.nef': 'Nikon RAW', 
            '.arw': 'Sony RAW',
            '.dng': 'Digital Negative',
            '.orf': 'Olympus RAW',
            '.rw2': 'Panasonic RAW'
        }
        
        if file_ext in raw_formats:
            metadata["RAW_Format"] = raw_formats[file_ext]
            metadata["RAW_File"] = "YES"
        else:
            metadata["RAW_File"] = "NO"
            
        return metadata
    
    def _process_exif_value(self, value):
        """Умная обработка значений EXIF"""
        try:
            if value is None:
                return None
                
            if isinstance(value, bytes):
                try:
                    # Пробуем декодировать
                    decoded = value.decode('utf-8', errors='ignore').strip()
                    if decoded and not all(c in ['\x00', ' '] for c in decoded):
                        return decoded
                    else:
                        return f"binary_data_{len(value)}_bytes"
                except:
                    return f"binary_data_{len(value)}_bytes"
                    
            elif hasattr(value, 'values'):
                # Обработка Ratio и других специальных типов
                try:
                    return str(value.values)
                except:
                    return str(value)
                    
            elif isinstance(value, (list, tuple)):
                # Обработка массивов
                if len(value) > 0:
                    return '|'.join(str(x) for x in value)
                else:
                    return None
                    
            else:
                # Простые типы
                str_value = str(value).strip()
                return str_value if str_value else None
                
        except Exception as e:
            return f"value_error_{str(e)}"
    
    def _convert_gps_coord(self, values):
        """Конвертация GPS координат в десятичные"""
        try:
            if len(values) >= 3:
                d = float(values[0])
                m = float(values[1])
                s = float(values[2])
                return d + (m / 60.0) + (s / 3600.0)
            elif len(values) == 2:
                return float(values[0]) + (float(values[1]) / 60.0)
            elif len(values) == 1:
                return float(values[0])
            else:
                return 0.0
        except:
            return 0.0
    
    def _decimal_to_dms(self, decimal, is_lat):
        """Конвертация десятичных градусов в DMS"""
        try:
            direction = 'N' if is_lat else 'E'
            if decimal < 0:
                direction = 'S' if is_lat else 'W'
                decimal = abs(decimal)
                
            degrees = int(decimal)
            minutes_decimal = (decimal - degrees) * 60
            minutes = int(minutes_decimal)
            seconds = (minutes_decimal - minutes) * 60
            
            return f"{degrees}° {minutes}' {seconds:.2f}\" {direction}"
        except:
            return "Conversion error"