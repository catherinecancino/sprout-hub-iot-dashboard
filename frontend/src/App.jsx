// frontend/src/App.jsx
import { useEffect, useState } from 'react';
import { db } from './firebase';
import { collection, query, where, orderBy, limit, onSnapshot } from 'firebase/firestore';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { Sprout, Droplets, Thermometer, Bell, Activity, Battery, WifiOff, Settings as SettingsIcon, Home, CheckCircle } from 'lucide-react';
import Chatbot from './components/Chatbot.jsx';
import Settings from './components/Settings.jsx';

function App() {
  const [nodes, setNodes] = useState({});
  const [nodeHistory, setNodeHistory] = useState({});
  const [alerts, setAlerts] = useState([]);
  const [selectedNode, setSelectedNode] = useState(null);
  const [loading, setLoading] = useState(true);
  const [newNodeNotification, setNewNodeNotification] = useState(null);
  const [currentView, setCurrentView] = useState('dashboard'); // NEW: 'dashboard' or 'settings'

  useEffect(() => {
    // Subscribe to all soil nodes
    const qNodes = query(collection(db, "nodes"));

    const unsubNodes = onSnapshot(qNodes, (snapshot) => {
      const nodesData = {};
      const previousNodeIds = Object.keys(nodes);
      
      snapshot.docs.forEach(docSnap => {
        const data = docSnap.data();
        nodesData[data.node_id] = {
          id: docSnap.id,
          ...data,
          latest: data.latest_readings || {}
        };
      });
      
      // Detect newly added nodes
      const currentNodeIds = Object.keys(nodesData);
      const newNodes = currentNodeIds.filter(id => !previousNodeIds.includes(id));
      
      if (newNodes.length > 0 && !loading) {
        newNodes.forEach(nodeId => {
          const nodeName = nodesData[nodeId].node_name || nodeId;
          setNewNodeNotification({
            nodeId,
            nodeName,
            timestamp: Date.now()
          });
          
          setTimeout(() => setNewNodeNotification(null), 5000);
        });
      }
      
      setNodes(nodesData);
      setLoading(false);
      
      if (!selectedNode && Object.keys(nodesData).length > 0) {
        setSelectedNode(Object.keys(nodesData)[0]);
      }
    });

    const qAlerts = query(
      collection(db, "alerts"),
      where("status", "==", "active"),
      orderBy("created_at", "desc"),
      limit(10)
    );

    const unsubAlerts = onSnapshot(qAlerts, (snapshot) => {
      const alertData = snapshot.docs.map(docSnap => ({
        id: docSnap.id,
        ...docSnap.data()
      }));
      setAlerts(alertData);
    });

    return () => {
      unsubNodes();
      unsubAlerts();
    };
  }, [selectedNode, loading]);

  useEffect(() => {
    if (!selectedNode) return;

    const readingsPath = `readings/${selectedNode}/history`;
    const qHistory = query(
      collection(db, readingsPath),
      orderBy("timestamp", "desc"),
      limit(20)
    );

    const unsubHistory = onSnapshot(qHistory, (snapshot) => {
      const data = snapshot.docs.map(docSnap => {
        const docData = docSnap.data();
        return {
          id: docSnap.id,
          ...docData,
          time: docData.timestamp?.seconds 
            ? new Date(docData.timestamp.seconds * 1000).toLocaleTimeString('en-US', { 
                hour: '2-digit', 
                minute: '2-digit' 
              })
            : 'N/A'
        };
      }).reverse();

      setNodeHistory(prev => ({
        ...prev,
        [selectedNode]: data
      }));
    });

    return () => unsubHistory();
  }, [selectedNode]);

  const currentNode = nodes[selectedNode];
  const currentHistory = nodeHistory[selectedNode] || [];
  const latest = currentNode?.latest || {};

  const getBatteryColor = (percentage) => {
    if (percentage > 60) return "text-green-600";
    if (percentage > 20) return "text-yellow-600";
    return "text-red-600";
  };

  const getConnectionStatus = (node) => {
    if (!node) return { color: "bg-gray-400", text: "Unknown" };
    if (node.status === "online") return { color: "bg-green-500", text: "Online" };
    return { color: "bg-red-500", text: "Offline" };
  };

  // If in settings view, show Settings page
  if (currentView === 'settings') {
    return (
      <div className="min-h-screen bg-gray-50">
        {/* Top Navigation Bar */}
        <div className="bg-white border-b border-gray-200 sticky top-0 z-40 shadow-sm">
          <div className="max-w-7xl mx-auto px-4 md:px-8 py-4 flex justify-between items-center">
            <h1 className="text-2xl font-bold text-gray-800 flex items-center gap-2">
              🌱 Sprout Hub
              <span className="text-sm bg-gray-100 text-gray-600 px-3 py-1 rounded-full font-normal">
                Settings
              </span>
            </h1>
            <button
              onClick={() => setCurrentView('dashboard')}
              className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 flex items-center gap-2 transition-all"
            >
              <Home size={18} />
              Back to Dashboard
            </button>
          </div>
        </div>

        {/* Settings Content */}
        <div className="p-4 md:p-8">
          <Settings />
        </div>

        {/* Chatbot (still available in settings) */}
        <Chatbot />
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-50">
        <div className="text-center">
          <Activity className="mx-auto mb-4 text-green-600 animate-pulse" size={48} />
          <p className="text-green-700 font-medium">Loading Sprout Hub System...</p>
          <p className="text-sm text-gray-500 mt-2">Detecting soil nodes...</p>
        </div>
      </div>
    );
  }

  if (Object.keys(nodes).length === 0) {
    return (
      <div className="flex h-screen items-center justify-center bg-gray-50">
        <div className="text-center max-w-md p-8 bg-white rounded-xl shadow-lg">
          <WifiOff className="mx-auto mb-4 text-yellow-600" size={48} />
          <h2 className="text-2xl font-bold text-gray-800 mb-2">No Soil Nodes Detected</h2>
          <p className="text-gray-600 mb-4">Waiting for soil nodes to come online...</p>
          
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
            <p className="text-sm text-blue-800 font-semibold mb-2">🔍 Auto-Detection Active</p>
            <p className="text-xs text-blue-700">
              New nodes will automatically appear when they send their first reading.
            </p>
          </div>
          
          <button 
            onClick={() => window.location.reload()} 
            className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700"
          >
            Refresh Page
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4 md:p-8">
      <div className="max-w-7xl mx-auto space-y-6">
        
        {/* New Node Notification */}
        {newNodeNotification && (
          <div className="fixed top-4 right-4 z-50 bg-green-600 text-white px-6 py-4 rounded-lg shadow-2xl animate-slide-in-right flex items-center gap-3">
            <CheckCircle className="text-green-200" size={24} />
            <div>
              <p className="font-bold">New Node Detected!</p>
              <p className="text-sm text-green-100">{newNodeNotification.nodeName} is now online</p>
            </div>
          </div>
        )}

        {/* Header with Settings Button */}
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-gray-800 flex items-center gap-2">
              🌱 Sprout Hub
              <span className="text-sm bg-green-100 text-green-700 px-3 py-1 rounded-full font-normal">
                {Object.keys(nodes).length} node{Object.keys(nodes).length > 1 ? 's' : ''} detected
              </span>
            </h1>
            <p className="text-sm text-gray-500 mt-1">
              Auto-detecting soil monitoring nodes
            </p>
          </div>
          
          <div className="flex gap-3 items-center">
            {/* Settings Button - NEW */}
            <button
              onClick={() => setCurrentView('settings')}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 flex items-center gap-2 transition-all"
            >
              <SettingsIcon size={18} />
              Settings
            </button>

            {/* Alerts */}
            <div className="relative">
              <Bell className="text-gray-600" size={24} />
              {alerts.length > 0 && (
                <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs w-5 h-5 rounded-full flex items-center justify-center font-bold">
                  {alerts.length}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Node Selector Tabs */}
        <div className="bg-white rounded-xl shadow-sm p-2 flex gap-2 overflow-x-auto">
          {Object.entries(nodes).map(([nodeId, nodeData]) => {
            const connectionStatus = getConnectionStatus(nodeData);
            const batteryPercentage = nodeData.latest?.battery_percentage || 0;
            const isNew = newNodeNotification?.nodeId === nodeId;
            
            return (
              <button
                key={nodeId}
                onClick={() => setSelectedNode(nodeId)}
                className={`px-6 py-3 rounded-lg font-medium transition-all whitespace-nowrap relative ${
                  selectedNode === nodeId
                    ? 'bg-green-600 text-white shadow-md'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                } ${isNew ? 'ring-2 ring-green-400 animate-pulse' : ''}`}
              >
                <div className="flex items-center gap-2">
                  {nodeData.node_name || nodeId.toUpperCase()}
                  
                  <span className={`inline-block w-2 h-2 ${connectionStatus.color} rounded-full ${
                    nodeData.status === 'online' ? 'animate-pulse' : ''
                  }`}></span>
                  
                  <Battery className={`${getBatteryColor(batteryPercentage)} ml-1`} size={16} />
                  <span className="text-xs">{batteryPercentage}%</span>
                  
                  {isNew && (
                    <span className="absolute -top-1 -right-1 bg-green-400 text-white text-xs px-2 py-0.5 rounded-full">
                      NEW
                    </span>
                  )}
                </div>
              </button>
            );
          })}
        </div>

        {/* Alerts Section */}
        {alerts.length > 0 && (
          <div className="bg-red-50 border-l-4 border-red-500 p-4 rounded-lg shadow-sm">
            <h3 className="font-bold text-red-700 mb-2 flex items-center gap-2">
              <Bell size={18} />
              Active Alerts ({alerts.length})
            </h3>
            <ul className="space-y-2">
              {alerts.map(alert => (
                <li key={alert.id} className="text-sm text-red-600 flex justify-between items-center bg-white p-2 rounded">
                  <span className="font-medium">{alert.message}</span>
                  <span className="text-xs text-red-400 bg-red-100 px-2 py-1 rounded uppercase">
                    {alert.severity}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Node Status Card */}
        <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-100">
          <div className="flex justify-between items-center">
            <div>
              <h3 className="text-lg font-semibold text-gray-700">
                {currentNode?.node_name || selectedNode}
              </h3>
              <p className="text-sm text-gray-500">
                Last seen: {currentNode?.last_seen?.seconds 
                  ? new Date(currentNode.last_seen.seconds * 1000).toLocaleString()
                  : 'Never'}
              </p>
            </div>
            <div className="flex items-center gap-4">
              {/* Battery Status */}
              <div className="text-center">
                <Battery className={`mx-auto ${getBatteryColor(latest.battery_percentage || 0)}`} size={32} />
                <p className="text-sm font-semibold mt-1">{latest.battery_percentage || 0}%</p>
                <p className="text-xs text-gray-500">Battery</p>
              </div>
              
              {/* Connection Status */}
              <div className="text-center">
                <div className={`w-12 h-12 rounded-full ${getConnectionStatus(currentNode).color} flex items-center justify-center`}>
                  {currentNode?.status === 'online' ? (
                    <Activity className="text-white" size={24} />
                  ) : (
                    <WifiOff className="text-white" size={24} />
                  )}
                </div>
                <p className="text-sm font-semibold mt-1">{getConnectionStatus(currentNode).text}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Soil Conditions Section */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
          <h2 className="text-xl font-semibold mb-4 text-gray-700 flex items-center gap-2">
            <Sprout className="text-green-600" size={24} />
            Soil Conditions
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card
              icon={<Droplets className="text-blue-500" />}
              label="Soil Moisture"
              value={`${latest.moisture || 0}%`}
              status={
                !latest.moisture ? "No Data" :
                latest.moisture < 30 ? "Critical" :
                latest.moisture > 80 ? "Too Wet" : "Optimal"
              }
              color={
                !latest.moisture ? "bg-gray-100" :
                latest.moisture < 30 ? "bg-red-100" :
                latest.moisture > 80 ? "bg-yellow-100" : "bg-blue-50"
              }
            />
            <Card
              icon={<Thermometer className="text-orange-500" />}
              label="Soil Temperature"
              value={`${latest.temperature || 0}°C`}
              status={
                !latest.temperature ? "No Data" :
                latest.temperature > 35 ? "Too Hot" :
                latest.temperature < 15 ? "Too Cold" : "Normal"
              }
              color={
                !latest.temperature ? "bg-gray-100" :
                latest.temperature > 35 || latest.temperature < 15 ? "bg-red-100" : "bg-orange-50"
              }
            />
            <Card
              icon={<Sprout className="text-green-500" />}
              label="Soil pH"
              value={latest.ph || 0}
              status={
                !latest.ph ? "No Data" :
                latest.ph < 5.5 ? "Too Acidic" :
                latest.ph > 7.5 ? "Too Alkaline" : "Neutral"
              }
              color={
                !latest.ph ? "bg-gray-100" :
                latest.ph < 5.5 || latest.ph > 7.5 ? "bg-yellow-100" : "bg-green-50"
              }
            />
          </div>
        </div>

        {/* Environmental Conditions Section */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
          <h2 className="text-xl font-semibold mb-4 text-gray-700 flex items-center gap-2">
            <Activity className="text-purple-600" size={24} />
            Environmental Conditions
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card
              icon={<Thermometer className="text-red-500" />}
              label="Air Temperature"
              value={`${latest.air_temperature || 0}°C`}
              status={
                !latest.air_temperature ? "No Data" :
                latest.air_temperature > 35 ? "Very Hot" :
                latest.air_temperature < 18 ? "Cool" : "Comfortable"
              }
              color={
                !latest.air_temperature ? "bg-gray-100" :
                latest.air_temperature > 35 ? "bg-red-100" :
                latest.air_temperature < 18 ? "bg-blue-100" : "bg-red-50"
              }
            />
            <Card
              icon={<Droplets className="text-cyan-500" />}
              label="Air Humidity"
              value={`${latest.humidity || 0}%`}
              status={
                !latest.humidity ? "No Data" :
                latest.humidity < 40 ? "Dry" :
                latest.humidity > 80 ? "Very Humid" : "Normal"
              }
              color={
                !latest.humidity ? "bg-gray-100" :
                latest.humidity < 40 ? "bg-yellow-100" :
                latest.humidity > 80 ? "bg-blue-100" : "bg-cyan-50"
              }
            />
          </div>
        </div>

        {/* NPK Values */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
          <h2 className="text-xl font-semibold mb-4 text-gray-700">NPK Levels</h2>
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center p-4 bg-blue-50 rounded-lg">
              <p className="text-sm text-gray-600">Nitrogen (N)</p>
              <p className="text-2xl font-bold text-blue-700">{latest.nitrogen || 0}</p>
              <p className="text-xs text-gray-500">mg/kg</p>
            </div>
            <div className="text-center p-4 bg-purple-50 rounded-lg">
              <p className="text-sm text-gray-600">Phosphorus (P)</p>
              <p className="text-2xl font-bold text-purple-700">{latest.phosphorus || 0}</p>
              <p className="text-xs text-gray-500">mg/kg</p>
            </div>
            <div className="text-center p-4 bg-green-50 rounded-lg">
              <p className="text-sm text-gray-600">Potassium (K)</p>
              <p className="text-2xl font-bold text-green-700">{latest.potassium || 0}</p>
              <p className="text-xs text-gray-500">mg/kg</p>
            </div>
          </div>
        </div>

        {/* Charts Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Soil Conditions Chart */}
          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
            <h2 className="text-xl font-semibold mb-4 text-gray-700">
              Soil Conditions - {currentNode?.node_name || selectedNode}
            </h2>
            <div className="h-80 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={currentHistory}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
                  <XAxis dataKey="time" tick={{ fontSize: 12 }} stroke="#9ca3af" />
                  <YAxis stroke="#9ca3af" />
                  <Tooltip contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} />
                  <Legend />
                  <Line type="monotone" dataKey="moisture" stroke="#3b82f6" strokeWidth={3} dot={false} activeDot={{ r: 6 }} name="Moisture %" />
                  <Line type="monotone" dataKey="temperature" stroke="#f97316" strokeWidth={3} dot={false} name="Soil Temp °C" />
                  <Line type="monotone" dataKey="ph" stroke="#10b981" strokeWidth={2} dot={false} name="pH" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Environmental Conditions Chart */}
          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
            <h2 className="text-xl font-semibold mb-4 text-gray-700">
              Environmental Conditions - {currentNode?.node_name || selectedNode}
            </h2>
            <div className="h-80 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={currentHistory}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
                  <XAxis dataKey="time" tick={{ fontSize: 12 }} stroke="#9ca3af" />
                  <YAxis stroke="#9ca3af" />
                  <Tooltip contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }} />
                  <Legend />
                  <Line type="monotone" dataKey="air_temperature" stroke="#ef4444" strokeWidth={3} dot={false} activeDot={{ r: 6 }} name="Air Temp °C" />
                  <Line type="monotone" dataKey="humidity" stroke="#06b6d4" strokeWidth={3} dot={false} name="Humidity %" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

      </div>

      {/* Chatbot Widget */}
      <Chatbot />
    </div>
  );
}

function Card({ icon, label, value, status, color }) {
  return (
    <div className={`${color} p-6 rounded-xl shadow-sm border border-gray-100 flex items-center justify-between transition-all hover:shadow-md`}>
      <div>
        <p className="text-gray-500 text-sm font-medium">{label}</p>
        <p className="text-3xl font-bold text-gray-800 my-1">{value}</p>
        <span className="text-xs font-bold px-2 py-1 rounded bg-white bg-opacity-60 text-gray-600 uppercase">
          {status}
        </span>
      </div>
      <div className="p-3 bg-gray-50 rounded-full shadow-inner">{icon}</div>
    </div>
  );
}

export default App;