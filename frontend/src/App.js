import React, { useState, useCallback, useEffect } from 'react';
import { ConfigProvider, message, Layout } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import axios from 'axios';
import MapComponent from './components/MapComponent';
import DataQueryPanel from './components/DataQueryPanel';
import ResultsPanel from './components/ResultsPanel';
import ProcessingConfigPanel from './components/ProcessingConfigPanel';
import './App.css';

const { Header, Content, Sider } = Layout;

// 配置 API 基础 URL
const API_BASE_URL = process.env.REACT_APP_API_URL || '';
axios.defaults.baseURL = API_BASE_URL;

function App() {
  const [aoi, setAoi] = useState(null);
  const [queryResults, setQueryResults] = useState([]);
  const [queryLoading, setQueryLoading] = useState(false);
  const [selectedImage, setSelectedImage] = useState(null);
  const [processingTask, setProcessingTask] = useState(null);
  const [processingLoading, setProcessingLoading] = useState(false);
  const [pollingInterval, setPollingInterval] = useState(null);

  // 处理 AOI 变化
  const handleAOIChange = useCallback((aoiGeoJSON) => {
    setAoi(aoiGeoJSON);
    if (aoiGeoJSON) {
      message.success('AOI 已更新');
      console.log('AOI GeoJSON:', aoiGeoJSON);
    } else {
      message.info('AOI 已清除');
    }
  }, []);

  // 处理数据查询
  const handleQuery = useCallback(async (queryParams) => {
    setQueryLoading(true);
    setQueryResults([]);
    
    try {
      console.log('查询参数:', queryParams);
      
      const response = await axios.post('/api/query', queryParams);
      
      if (response.data && response.data.results) {
        setQueryResults(response.data.results);
        message.success(`查询成功，找到 ${response.data.results.length} 个影像`);
      } else {
        setQueryResults([]);
        message.info('未找到符合条件的影像');
      }
    } catch (error) {
      console.error('查询失败:', error);
      message.error(error.response?.data?.message || '查询失败，请稍后重试');
      setQueryResults([]);
    } finally {
      setQueryLoading(false);
    }
  }, []);

  // 处理影像选择
  const handleImageSelect = useCallback((image) => {
    console.log('选中影像:', image);
    setSelectedImage(image);
    message.info(`已选择影像: ${image.id}`);
  }, []);

  // 轮询任务状态
  const pollTaskStatus = useCallback(async (taskId) => {
    try {
      const response = await axios.get(`/api/process/tasks/${taskId}`);
      const task = response.data;
      
      setProcessingTask(task);
      
      // 如果任务完成或失败，停止轮询
      if (task.status === 'completed' || task.status === 'failed') {
        if (pollingInterval) {
          clearInterval(pollingInterval);
          setPollingInterval(null);
        }
        
        if (task.status === 'completed') {
          message.success('处理完成！');
        } else {
          message.error('处理失败');
        }
      }
    } catch (error) {
      console.error('查询任务状态失败:', error);
      // 不显示错误消息，避免频繁提示
    }
  }, [pollingInterval]);

  // 启动轮询
  const startPolling = useCallback((taskId) => {
    // 清除现有的轮询
    if (pollingInterval) {
      clearInterval(pollingInterval);
    }
    
    // 立即查询一次
    pollTaskStatus(taskId);
    
    // 设置定时轮询（每 5 秒）
    const interval = setInterval(() => {
      pollTaskStatus(taskId);
    }, 5000);
    
    setPollingInterval(interval);
  }, [pollingInterval, pollTaskStatus]);

  // 停止轮询
  const stopPolling = useCallback(() => {
    if (pollingInterval) {
      clearInterval(pollingInterval);
      setPollingInterval(null);
    }
  }, [pollingInterval]);

  // 处理植被指数计算
  const handleProcess = useCallback(async ({ image, indices }) => {
    setProcessingLoading(true);
    setProcessingTask(null);
    
    try {
      console.log('🔍 [DEBUG] 开始处理参数:', { image, indices });
      console.log('🔍 [DEBUG] 可用的资产键:', Object.keys(image.assets || {}));
      
      // 构建波段 URL 映射
      const bandUrls = {};
      if (image.assets) {
        // 直接使用 STAC API 返回的标准资产键名
        // 优先使用 COG 格式（不带 -jp2 后缀）
        const standardBandKeys = {
          'red': 'red',       // B04 红光
          'nir': 'nir',       // B08 近红外
          'green': 'green',   // B03 绿光
          'blue': 'blue'      // B02 蓝光
        };
        
        // 精确匹配标准波段键名
        for (const [bandName, assetKey] of Object.entries(standardBandKeys)) {
          if (image.assets[assetKey] && image.assets[assetKey].href) {
            // 确保不是 -jp2 后缀的资产
            if (!assetKey.endsWith('-jp2')) {
              bandUrls[bandName] = image.assets[assetKey].href;
              console.log(`🔍 [DEBUG] 匹配波段 ${bandName}: ${assetKey} -> ${image.assets[assetKey].href.slice(-50)}`);
            }
          }
        }
        
        // 如果标准键名没有找到，尝试备用键名
        if (!bandUrls.nir && image.assets['nir08']) {
          bandUrls.nir = image.assets['nir08'].href;
          console.log('🔍 [DEBUG] 使用备用 nir08 作为 nir');
        }
      }
      
      // 转换 S3 URL 为 HTTPS URL（用于公开访问）
      const convertS3ToHttps = (url) => {
        if (url.startsWith('s3://sentinel-s2-l2a/')) {
          // 转换为 Element84 的公开 HTTPS 端点
          // s3://sentinel-s2-l2a/tiles/... → https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/tiles/...
          return url.replace(
            's3://sentinel-s2-l2a/',
            'https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/'
          );
        }
        return url;
      };
      
      // 应用 URL 转换
      const convertedBandUrls = {};
      Object.keys(bandUrls).forEach(key => {
        convertedBandUrls[key] = convertS3ToHttps(bandUrls[key]);
      });
      
      const requestData = {
        image_id: image.id,
        indices: indices,
        aoi: aoi,
        output_format: 'COG',
        band_urls: convertedBandUrls
      };
      
      console.log('🔍 [DEBUG] 提交处理请求:', requestData);
      console.log('🔍 [DEBUG] 原始波段 URLs:', bandUrls);
      console.log('🔍 [DEBUG] 转换后波段 URLs:', convertedBandUrls);
      console.log('🔍 [DEBUG] 代码版本: 2026-01-27-v2');
      
      // 验证是否有必需的波段
      const requiredBands = indices.includes('EVI') ? ['red', 'nir', 'blue'] : ['red', 'nir'];
      const missingBands = requiredBands.filter(band => !convertedBandUrls[band]);
      
      if (missingBands.length > 0) {
        message.error(`缺少必需的波段: ${missingBands.join(', ')}`);
        console.error('可用的资产:', Object.keys(image.assets || {}));
        setProcessingLoading(false);
        return;
      }
      
      const response = await axios.post('/api/process/indices', requestData);
      
      if (response.data && response.data.task_id) {
        const task = {
          task_id: response.data.task_id,
          status: response.data.status,
          progress: 0
        };
        
        setProcessingTask(task);
        message.success('处理任务已创建');
        
        // 开始轮询任务状态
        startPolling(response.data.task_id);
      }
    } catch (error) {
      console.error('处理失败:', error);
      message.error(error.response?.data?.detail || '处理失败，请稍后重试');
    } finally {
      setProcessingLoading(false);
    }
  }, [aoi, startPolling]);

  // 组件卸载时清理轮询
  useEffect(() => {
    return () => {
      if (pollingInterval) {
        clearInterval(pollingInterval);
      }
    };
  }, [pollingInterval]);

  // 处理下载
  const handleDownload = useCallback((image) => {
    console.log('下载影像:', image);
    message.info('下载功能将在后续实现');
    // 未来实现：调用下载 API 或直接下载文件
  }, []);

  // 取消任务
  const handleCancelTask = useCallback(async (taskId) => {
    try {
      await axios.delete(`/api/process/tasks/${taskId}`);
      message.success('任务已取消');
      
      // 停止轮询
      stopPolling();
      
      // 刷新任务状态
      const response = await axios.get(`/api/process/tasks/${taskId}`);
      setProcessingTask(response.data);
    } catch (error) {
      console.error('取消任务失败:', error);
      message.error(error.response?.data?.detail || '取消任务失败');
    }
  }, [stopPolling]);

  // 刷新任务状态
  const handleRefreshTask = useCallback(async (taskId) => {
    try {
      const response = await axios.get(`/api/process/tasks/${taskId}`);
      setProcessingTask(response.data);
      message.success('任务状态已刷新');
      
      // 如果任务正在进行且没有轮询，启动轮询
      const task = response.data;
      if ((task.status === 'queued' || task.status === 'running') && !pollingInterval) {
        startPolling(taskId);
      }
    } catch (error) {
      console.error('刷新任务状态失败:', error);
      message.error(error.response?.data?.detail || '刷新任务状态失败');
    }
  }, [pollingInterval, startPolling]);

  return (
    <ConfigProvider locale={zhCN}>
      <Layout className="app">
        <Header className="app-header">
          <h1>卫星 GIS 平台</h1>
          <p>基于 AWS Open Data 的遥感数据处理应用</p>
        </Header>
        <Layout className="app-main">
          {/* 左侧查询面板 */}
          <Sider 
            width={320} 
            theme="light"
            className="app-sider"
          >
            <DataQueryPanel
              satellites={['sentinel-2']}
              onQuery={handleQuery}
              aoi={aoi}
              loading={queryLoading}
            />
          </Sider>

          {/* 中间地图区域 */}
          <Content className="app-content">
            <MapComponent
              mapProvider="osm"
              center={[39.9, 116.4]}
              zoom={5}
              onAOIChange={handleAOIChange}
            />
          </Content>

          {/* 右侧面板 */}
          <Sider 
            width={400} 
            theme="light"
            className="app-sider app-sider-right"
          >
            <div className="right-panel-container">
              {/* 结果面板 */}
              <div className="results-panel-wrapper">
                <ResultsPanel
                  results={queryResults}
                  loading={queryLoading}
                  onImageSelect={handleImageSelect}
                  onDownload={handleDownload}
                  selectedImageId={selectedImage?.id}
                />
              </div>
              
              {/* 处理配置面板 */}
              <div className="processing-panel-wrapper">
                <ProcessingConfigPanel
                  availableIndices={['NDVI', 'SAVI', 'EVI', 'VGI']}
                  onProcess={handleProcess}
                  selectedImage={selectedImage}
                  processingTask={processingTask}
                  disabled={processingLoading}
                  onCancelTask={handleCancelTask}
                  onRefreshTask={handleRefreshTask}
                />
              </div>
            </div>
          </Sider>
        </Layout>
      </Layout>
    </ConfigProvider>
  );
}

export default App;
