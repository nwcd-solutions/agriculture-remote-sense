import React, { useState, useCallback, useEffect } from 'react';
import { ConfigProvider, message, Layout, Button, Space, Avatar, Dropdown } from 'antd';
import { UserOutlined, LogoutOutlined } from '@ant-design/icons';
import zhCN from 'antd/locale/zh_CN';
import { Amplify } from 'aws-amplify';
import axios from 'axios';
import AuthWrapper from './components/AuthWrapper';
import MapComponent from './components/MapComponent';
import DataQueryPanel from './components/DataQueryPanel';
import ResultsPanel from './components/ResultsPanel';
import ProcessingConfigPanel from './components/ProcessingConfigPanel';
import { awsConfig } from './config/aws-config';
import './App.css';

// Configure Amplify
if (awsConfig.Auth?.Cognito?.userPoolId && awsConfig.Auth?.Cognito?.userPoolClientId) {
  Amplify.configure(awsConfig);
}

const { Header, Content, Sider } = Layout;

// 配置 API 基础 URL
const API_BASE_URL = process.env.REACT_APP_API_URL || '';
const API_KEY = process.env.REACT_APP_API_KEY || '';

// 配置 axios 默认值
axios.defaults.baseURL = API_BASE_URL;

// 添加请求拦截器，自动添加 API Key
axios.interceptors.request.use(
  (config) => {
    if (API_KEY) {
      config.headers['X-Api-Key'] = API_KEY;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

function App() {
  // Check if Cognito is configured
  const cognitoEnabled = awsConfig.Auth?.Cognito?.userPoolId && awsConfig.Auth?.Cognito?.userPoolClientId;

  const AppContent = ({ signOut, user }) => {
    const [aoi, setAoi] = useState(null);
  const [queryResults, setQueryResults] = useState([]);
  const [queryLoading, setQueryLoading] = useState(false);
  const [selectedImage, setSelectedImage] = useState(null);
  const [processingTask, setProcessingTask] = useState(null);
  const [processingLoading, setProcessingLoading] = useState(false);
  const [pollingInterval, setPollingInterval] = useState(null);

  // User menu items
  const userMenuItems = [
    {
      key: 'user',
      label: user?.signInDetails?.loginId || user?.username || '用户',
      disabled: true,
    },
    {
      type: 'divider',
    },
    {
      key: 'logout',
      label: '退出登录',
      icon: <LogoutOutlined />,
      onClick: signOut,
    },
  ];

  // 处理 AOI 变化
  const handleAOIChange = useCallback((aoiGeoJSON) => {
    setAoi(aoiGeoJSON);
    console.log('AOI GeoJSON:', aoiGeoJSON);
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
  }, []);

  // 处理时间合成
  const handleComposite = useCallback(async ({ results, compositeMode, applyCloudMask, satellite, indices, aoi: compositeAoi }) => {
    setProcessingLoading(true);
    setProcessingTask(null);

    try {
      // 从查询结果中提取影像 URL 和时间戳
      // 对于 Sentinel-2，使用 visual 或 nir 波段作为合成输入
      const imageUrls = [];
      const imageTimestamps = [];
      const qaBandUrls = [];

      for (const img of results) {
        // 找到一个可用的波段 URL
        let bandUrl = null;
        const assets = img.assets || {};
        // 优先使用 nir 波段，其次 red，最后 visual
        for (const key of ['nir', 'nir08', 'red', 'B04', 'visual']) {
          if (assets[key]?.href) {
            bandUrl = assets[key].href;
            break;
          }
        }
        if (!bandUrl) continue;

        imageUrls.push(bandUrl);
        imageTimestamps.push(img.datetime);

        // QA 波段 URL（用于云掩膜）
        let qaUrl = null;
        if (applyCloudMask) {
          if (satellite === 'sentinel-2' && assets['SCL']?.href) {
            qaUrl = assets['SCL'].href;
          } else if (satellite === 'landsat-8' && assets['qa_pixel']?.href) {
            qaUrl = assets['qa_pixel'].href;
          }
        }
        qaBandUrls.push(qaUrl);
      }

      if (imageUrls.length === 0) {
        message.error('没有可用的影像 URL');
        setProcessingLoading(false);
        return;
      }

      const requestData = {
        satellite,
        composite_mode: compositeMode,
        apply_cloud_mask: applyCloudMask,
        aoi: compositeAoi,
        image_urls: imageUrls,
        image_timestamps: imageTimestamps,
        qa_band_urls: qaBandUrls,
        indices,
      };

      console.log('提交时间合成:', requestData);

      const response = await axios.post('/api/process/composite', requestData);

      if (response.data?.task_id) {
        setProcessingTask({
          task_id: response.data.task_id,
          task_type: 'composite',
          status: response.data.status,
          progress: 0,
        });
        startPolling(response.data.task_id);
      }
    } catch (error) {
      console.error('时间合成提交失败:', error);
      message.error(error.response?.data?.error || '时间合成提交失败');
    } finally {
      setProcessingLoading(false);
    }
  }, [startPolling]);

  // 取消任务
  const handleCancelTask = useCallback(async (taskId) => {
    try {
      await axios.delete(`/api/process/tasks/${taskId}`);
      
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
      console.log('刷新任务状态:', taskId);
      const response = await axios.get(`/api/process/tasks/${taskId}`);
      console.log('任务状态响应:', response.data);
      setProcessingTask(response.data);
      
      // 如果任务正在进行且没有轮询，启动轮询
      const task = response.data;
      if ((task.status === 'queued' || task.status === 'running') && !pollingInterval) {
        startPolling(taskId);
      }
    } catch (error) {
      console.error('刷新任务状态失败:', error);
      console.error('错误详情:', error.response?.data);
      const errorMsg = error.response?.data?.error || error.response?.data?.detail || error.message || '刷新任务状态失败';
      message.error(`刷新失败: ${errorMsg}`);
    }
  }, [pollingInterval, startPolling]);

  return (
    <ConfigProvider locale={zhCN}>
      <Layout className="app">
        <Header className="app-header">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
            <div>
              <h1>卫星 GIS 平台</h1>
              <p>基于 AWS Open Data 的遥感数据处理应用</p>
            </div>
            {cognitoEnabled && user && (
              <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
                <Space style={{ cursor: 'pointer', color: 'white' }}>
                  <Avatar icon={<UserOutlined />} />
                  <span>{user?.attributes?.name || user?.username || '用户'}</span>
                </Space>
              </Dropdown>
            )}
          </div>
        </Header>
        <Layout className="app-main">
          {/* 左侧查询面板 */}
          <Sider 
            width={320} 
            theme="light"
            className="app-sider"
          >
            <DataQueryPanel
              satellites={['sentinel-2', 'sentinel-1', 'landsat-8', 'modis']}
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
                  onComposite={handleComposite}
                  selectedImage={selectedImage}
                  queryResults={queryResults}
                  processingTask={processingTask}
                  disabled={processingLoading}
                  onCancelTask={handleCancelTask}
                  onRefreshTask={handleRefreshTask}
                  aoi={aoi}
                  satelliteType={selectedImage?.satellite || 'sentinel-2'}
                />
              </div>
            </div>
          </Sider>
        </Layout>
      </Layout>
    </ConfigProvider>
  );
  };

  // Wrap with AuthWrapper if Cognito is enabled
  if (cognitoEnabled) {
    return (
      <AuthWrapper>
        {({ signOut, user }) => <AppContent signOut={signOut} user={user} />}
      </AuthWrapper>
    );
  }

  // Otherwise render without authentication
  return <AppContent signOut={() => {}} user={null} />;
}

export default App;
