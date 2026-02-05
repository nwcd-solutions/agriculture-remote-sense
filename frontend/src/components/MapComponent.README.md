# MapComponent

地图组件 - 地图显示和交互的核心组件

## 功能特性

- ✅ 集成 Leaflet 地图库
- ✅ 支持 OpenStreetMap 作为默认地图服务
- ✅ 地图平移、缩放等基础交互
- ✅ AOI（感兴趣区域）绘制功能
- ✅ 多边形绘制工具
- ✅ GeoJSON 格式输出
- ✅ AOI 边界显示和编辑

## 使用方法

### 基础用法

```jsx
import MapComponent from './components/MapComponent';

function App() {
  const handleAOIChange = (aoiGeoJSON) => {
    console.log('AOI changed:', aoiGeoJSON);
  };

  return (
    <MapComponent
      mapProvider="osm"
      center={[39.9, 116.4]}
      zoom={10}
      onAOIChange={handleAOIChange}
    />
  );
}
```

### 属性 (Props)

| 属性 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `mapProvider` | string | 'osm' | 地图服务提供商 (osm/baidu/amap/tianditu/mapbox) |
| `center` | [number, number] | [39.9, 116.4] | 地图中心坐标 [纬度, 经度] |
| `zoom` | number | 10 | 缩放级别 (2-19) |
| `layers` | array | [] | 图层配置数组 |
| `onAOIChange` | function | - | AOI 变化回调函数 |

### 方法

组件通过 ref 暴露以下方法：

- `drawPolygon()` - 启动多边形绘制模式
- `loadAOI(geojson)` - 加载 GeoJSON AOI
- `clearAOI()` - 清除当前 AOI

### AOI 绘制

用户可以通过以下方式绘制 AOI：

1. 点击地图右上角的多边形绘制按钮
2. 在地图上点击创建多边形顶点
3. 双击或点击第一个点完成绘制
4. 绘制完成后，`onAOIChange` 回调会被调用，传入 GeoJSON 格式的 AOI

### GeoJSON 格式

AOI 以标准 GeoJSON 格式输出：

```json
{
  "type": "Polygon",
  "coordinates": [
    [
      [116.3, 39.9],
      [116.4, 39.9],
      [116.4, 40.0],
      [116.3, 40.0],
      [116.3, 39.9]
    ]
  ]
}
```

## 依赖

- `leaflet` ^1.9.4 - 地图库
- `leaflet-draw` ^1.0.4 - 绘制工具
- `react-leaflet` ^4.2.1 - React 封装
- `react-leaflet-draw` ^0.20.4 - 绘制工具 React 封装

## 样式

组件使用以下 CSS 文件：

- `leaflet/dist/leaflet.css` - Leaflet 基础样式
- `leaflet-draw/dist/leaflet.draw.css` - 绘制工具样式
- `MapComponent.css` - 自定义样式

## 验证需求

该组件实现了以下需求：

- **需求 8.1** - 真实地图服务集成（OpenStreetMap）
- **需求 8.2** - 地图交互功能（平移、缩放）
- **需求 8.2.1** - 基础地图显示
- **需求 2.1** - 交互式 AOI 定义（多边形绘制）
- **需求 2.5** - AOI 边界显示

## 未来扩展

- [ ] 支持更多地图服务（百度、高德、天地图）
- [ ] 坐标系转换（WGS84/GCJ02/BD09）
- [ ] 图层管理功能
- [ ] 测量工具（距离、面积）
- [ ] 地图打印和截图
