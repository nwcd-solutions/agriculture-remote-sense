import { render, screen } from '@testing-library/react';
import App from './App';

// Mock the MapComponent to avoid Leaflet dependencies in tests
jest.mock('./components/MapComponent');

test('renders app header', () => {
  render(<App />);
  const headerElement = screen.getByText(/卫星 GIS 平台/i);
  expect(headerElement).toBeInTheDocument();
});

test('renders app description', () => {
  render(<App />);
  const descElement = screen.getByText(/基于 AWS Open Data 的遥感数据处理应用/i);
  expect(descElement).toBeInTheDocument();
});

test('renders map component', () => {
  render(<App />);
  const mapElement = screen.getByTestId('map-component');
  expect(mapElement).toBeInTheDocument();
});
