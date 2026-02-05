import React, { useRef, useCallback, useEffect } from 'react';
import { MapContainer, TileLayer, FeatureGroup } from 'react-leaflet';
import { EditControl } from 'react-leaflet-draw';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import 'leaflet-draw/dist/leaflet.draw.css';
import './MapComponent.css';

// Fix for default marker icons in Leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: require('leaflet/dist/images/marker-icon-2x.png'),
  iconUrl: require('leaflet/dist/images/marker-icon.png'),
  shadowUrl: require('leaflet/dist/images/marker-shadow.png'),
});

/**
 * 地图组件 - 地图显示和交互的核心组件
 * 
 * 属性：
 * - mapProvider: 地图服务提供商（baidu/amap/tianditu/osm/mapbox）
 * - center: 地图中心坐标 [lat, lon]
 * - zoom: 缩放级别
 * - layers: 图层配置数组
 * - onAOIChange: AOI 变化回调函数
 * 
 * 方法：
 * - drawPolygon(): 启动多边形绘制模式
 * - loadAOI(geojson): 加载 GeoJSON AOI
 * - clearAOI(): 清除当前 AOI
 * - switchMapProvider(provider): 切换地图服务
 * - addLayer(layer): 添加图层
 * - removeLayer(layerId): 移除图层
 */
const MapComponent = ({ 
  mapProvider = 'osm',
  center = [39.9, 116.4],
  zoom = 10,
  layers = [],
  onAOIChange 
}) => {
  const featureGroupRef = useRef(null);
  const mapRef = useRef(null);

  // 获取地图瓦片 URL
  const getTileLayerUrl = () => {
    switch (mapProvider) {
      case 'osm':
      default:
        return 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
    }
  };

  // 获取地图归属信息
  const getAttribution = () => {
    switch (mapProvider) {
      case 'osm':
      default:
        return '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';
    }
  };

  // 将 Leaflet 图层转换为 GeoJSON
  const layerToGeoJSON = useCallback((layer) => {
    if (layer.toGeoJSON) {
      return layer.toGeoJSON();
    }
    return null;
  }, []);

  // 处理绘制创建事件
  const handleCreated = useCallback((e) => {
    const { layer } = e;
    const geojson = layerToGeoJSON(layer);
    
    if (geojson && onAOIChange) {
      // 转换为标准 GeoJSON 格式
      const aoiGeoJSON = {
        type: geojson.geometry.type,
        coordinates: geojson.geometry.coordinates
      };
      onAOIChange(aoiGeoJSON);
    }
  }, [layerToGeoJSON, onAOIChange]);

  // 处理绘制编辑事件
  const handleEdited = useCallback((e) => {
    const { layers } = e;
    layers.eachLayer((layer) => {
      const geojson = layerToGeoJSON(layer);
      if (geojson && onAOIChange) {
        const aoiGeoJSON = {
          type: geojson.geometry.type,
          coordinates: geojson.geometry.coordinates
        };
        onAOIChange(aoiGeoJSON);
      }
    });
  }, [layerToGeoJSON, onAOIChange]);

  // 处理绘制删除事件
  const handleDeleted = useCallback(() => {
    if (onAOIChange) {
      onAOIChange(null);
    }
  }, [onAOIChange]);

  // 启动多边形绘制模式
  const drawPolygon = useCallback(() => {
    if (mapRef.current) {
      // 触发绘制工具的多边形绘制
      const drawControl = document.querySelector('.leaflet-draw-draw-polygon');
      if (drawControl) {
        drawControl.click();
      }
    }
  }, []);

  // 加载 GeoJSON AOI
  const loadAOI = useCallback((geojson) => {
    if (featureGroupRef.current && geojson) {
      // 清除现有图层
      featureGroupRef.current.clearLayers();
      
      // 添加新的 GeoJSON 图层
      const geoJsonLayer = L.geoJSON(geojson);
      geoJsonLayer.eachLayer((layer) => {
        featureGroupRef.current.addLayer(layer);
      });

      // 缩放到 AOI 范围
      if (mapRef.current) {
        const bounds = featureGroupRef.current.getBounds();
        if (bounds.isValid()) {
          mapRef.current.fitBounds(bounds);
        }
      }
    }
  }, []);

  // 清除当前 AOI
  const clearAOI = useCallback(() => {
    if (featureGroupRef.current) {
      featureGroupRef.current.clearLayers();
      if (onAOIChange) {
        onAOIChange(null);
      }
    }
  }, [onAOIChange]);

  // 暴露方法给父组件
  useEffect(() => {
    if (mapRef.current) {
      mapRef.current.drawPolygon = drawPolygon;
      mapRef.current.loadAOI = loadAOI;
      mapRef.current.clearAOI = clearAOI;
    }
  }, [drawPolygon, loadAOI, clearAOI]);

  return (
    <div className="map-component">
      <MapContainer
        center={center}
        zoom={zoom}
        style={{ width: '100%', height: '100%' }}
        ref={mapRef}
      >
        <TileLayer
          url={getTileLayerUrl()}
          attribution={getAttribution()}
          maxZoom={19}
          minZoom={2}
        />
        
        <FeatureGroup ref={featureGroupRef}>
          <EditControl
            position="topright"
            onCreated={handleCreated}
            onEdited={handleEdited}
            onDeleted={handleDeleted}
            draw={{
              rectangle: false,
              circle: false,
              circlemarker: false,
              marker: false,
              polyline: false,
              polygon: {
                allowIntersection: false,
                showArea: true,
                shapeOptions: {
                  color: '#3388ff',
                  weight: 2,
                  fillOpacity: 0.2
                }
              }
            }}
            edit={{
              edit: true,
              remove: true
            }}
          />
        </FeatureGroup>
      </MapContainer>
    </div>
  );
};

export default MapComponent;
