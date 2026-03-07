// frontend/src/App.jsx
import { useEffect, useState } from 'react';
import { db } from './firebase';
import { collection, query, where, orderBy, limit, onSnapshot } from 'firebase/firestore';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { Sprout, Droplets, Thermometer, Bell, Activity, WifiOff, Settings as SettingsIcon, Home, CheckCircle } from 'lucide-react';
import Chatbot from './components/Chatbot.jsx';
import Settings from './components/Settings.jsx';

function App() {
  const [nodes, setNodes] = useState({});
  const [nodeHistory, setNodeHistory] = useState({});
  const [alerts, setAlerts] = useState([]);
  const [selectedNode, setSelectedNode] = useState(null);
  const [loading, setLoading] = useState(true);
  const [newNodeNotification, setNewNodeNotification] = useState(null);
  const [currentView, setCurrentView] = useState('dashboard');
  const [cropProfiles, setCropProfiles] = useState([]);  
  const [assigningCrop, setAssigningCrop] = useState(false);  

  const API_BASE = 'http://127.0.0.1:8000/api/v1';

  // Helper function to properly format values and round to 1 decimal place
  const formatValue = (val, unit = '') => {
    if (val === undefined || val === null) return 'No Data';
    
    const num = Number(val);
    if (!isNaN(num)) {
      return `${num.toFixed(1)}${unit}`;
    }
    
    return `${val}${unit}`;
  };

  // Helper to check if value exists
  const hasValue = (value) => {
    return value !== undefined && value !== null;
  };

  // Load crop profiles on mount
  useEffect(() => {
    const loadCropProfiles = async () => {
      try {
        const response = await fetch(`${API_BASE}/knowledge-library/`);
        if (response.ok) {
          const data = await response.json();
          console.log('✓ Loaded crop profiles:', data);
          const profilesArray = data.crops || data || [];
          setCropProfiles(profilesArray);
          console.log('Set crop profiles array:', profilesArray);
        } else {
          console.error('Failed to load crop profiles');
        }
      } catch (err) {
        console.error('Error loading crop profiles:', err);
      }
    };

    loadCropProfiles();
  }, []);

  // Function to assign crop to node
  const assignCropToNode = async (nodeId, cropType) => {
    if (!nodeId || nodeId === 'undefined' || !cropType) {
      console.error('Invalid nodeId or cropType:', { nodeId, cropType });
      alert('❌ Error: Invalid Node ID detected. Check your Firebase database for missing node_id fields.');
      return;
    }
    
    setAssigningCrop(true);
    
    try {
      console.log(`Assigning ${cropType} to ${nodeId}...`);
      
      const response = await fetch(`${API_BASE}/nodes/${nodeId}/assign-crop/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ crop_type: cropType })
      });

      if (response.ok) {
        const data = await response.json();
        console.log('✓ Crop assigned successfully:', data);
        
        // Update local state immediately for instant UI feedback
        setNodes(prev => ({
          ...prev,
          [nodeId]: {
            ...prev[nodeId],
            crop_type: cropType
          }
        }));
        
        // Show success notification
        const nodeName = nodes[nodeId]?.node_name || nodeId;
        const cropName = cropProfiles.find(p => p.crop_id === cropType)?.crop_name || cropType;
        alert(`✅ Successfully assigned "${cropName}" to ${nodeName}\n\nThresholds will now use crop-specific values from uploaded documents.`);
      } else {
        const error = await response.json();
        console.error('Failed to assign crop:', error);
        alert(`❌ Failed to assign crop: ${error.error || 'Unknown error'}`);
      }
    } catch (err) {
      console.error('Error assigning crop:', err);
      alert('❌ Network error. Please check your connection and try again.');
    } finally {
      setAssigningCrop(false);
    }
  };

  useEffect(() => {
    // Subscribe to all soil nodes
    const qNodes = query(collection(db, "nodes"));

    const unsubNodes = onSnapshot(qNodes, (snapshot) => {
      const nodesData = {};
      const previousNodeIds = Object.keys(nodes);
      
      snapshot.docs.forEach(docSnap => {
        const data = docSnap.data();
        const lastReading = data.lastReading || data.latest_readings || {};
        
        const sensorData = {
          moisture: lastReading.moisture !== undefined ? lastReading.moisture : data.moisture,
          ph: lastReading.ph !== undefined ? lastReading.ph : (lastReading.pH !== undefined ? lastReading.pH : (data.ph !== undefined ? data.ph : data.pH)),
          temperature: lastReading.temperature !== undefined ? lastReading.temperature : data.temperature,
          nitrogen: lastReading.nitrogen !== undefined ? lastReading.nitrogen : data.nitrogen,
          phosphorus: lastReading.phosphorus !== undefined ? lastReading.phosphorus : data.phosphorus,
          potassium: lastReading.potassium !== undefined ? lastReading.potassium : data.potassium,
          air_temperature: lastReading.air_temperature !== undefined ? lastReading.air_temperature : data.air_temperature,
          humidity: lastReading.humidity !== undefined ? lastReading.humidity : data.humidity,
          battery_percentage: lastReading.battery_percentage !== undefined ? lastReading.battery_percentage : data.battery_percentage,
          ec: lastReading.ec !== undefined ? lastReading.ec : data.ec
        };
        
        const safeNodeId = data.node_id || docSnap.id;
        
        nodesData[safeNodeId] = {
          id: docSnap.id,
          ...data,
          node_id: safeNodeId,
          latest: sensorData
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

  // Default fallback thresholds 
  const defaultThresholds = {
    moisture: { min: 30.0, max: 80.0 },
    temperature: { min: 15.0, max: 35.0 },
    ph: { min: 5.5, max: 7.5 },
    nitrogen: { min: 50.0, max: 150.0 },
    phosphorus: { min: 20.0, max: 80.0 },
    potassium: { min: 50.0, max: 200.0 }
  };

  const getDynamicStatus = (sensorType, value, activeProfile) => {
    if (!hasValue(value)) return { label: "No Data", color: "bg-gray-100" };

    const numValue = Number(value);
    let rules = defaultThresholds[sensorType];

    // Pull database rules if active
    if (activeProfile && activeProfile.thresholds) {
      const t = activeProfile.thresholds;
      
      if (sensorType === 'moisture' && t.moisture_min !== undefined) rules = { min: t.moisture_min, max: t.moisture_max };
      if (sensorType === 'temperature' && t.temp_min !== undefined) rules = { min: t.temp_min, max: t.temp_max };
      if (sensorType === 'ph' && t.ph_min !== undefined) rules = { min: t.ph_min, max: t.ph_max };
      
      if (sensorType === 'nitrogen' && t.nitrogen_min !== undefined) rules = { min: t.nitrogen_min, max: t.nitrogen_max };
      if (sensorType === 'phosphorus' && t.phosphorus_min !== undefined) rules = { min: t.phosphorus_min, max: t.phosphorus_max };
      if (sensorType === 'potassium' && t.potassium_min !== undefined) rules = { min: t.potassium_min, max: t.potassium_max };
    }

    // Status logic
    if (sensorType === 'moisture') {
      if (numValue < rules.min) return { label: "Too Dry", color: "bg-red-100" };
      if (numValue > rules.max) return { label: "Too Wet", color: "bg-blue-100" };
      return { label: "Optimal", color: "bg-green-50" };
    }
    if (sensorType === 'temperature') {
      if (numValue < rules.min) return { label: "Too Cold", color: "bg-blue-100" };
      if (numValue > rules.max) return { label: "Too Hot", color: "bg-red-100" };
      return { label: "Optimal", color: "bg-green-50" };
    }
    if (sensorType === 'ph') {
      if (numValue < rules.min) return { label: "Too Acidic", color: "bg-yellow-100" };
      if (numValue > rules.max) return { label: "Too Alkaline", color: "bg-yellow-100" };
      return { label: "Optimal", color: "bg-green-50" };
    }
    // NPK Logic
    if (['nitrogen', 'phosphorus', 'potassium'].includes(sensorType)) {
      if (numValue < rules.min) return { label: "Too Low", color: "bg-orange-100" };
      if (numValue > rules.max) return { label: "Too High", color: "bg-red-100" };
      return { label: "Optimal", color: "bg-green-50" };
    }
    // 🌤️ NEW: Static Environmental Logic
    if (sensorType === 'air_temperature') {
      if (numValue > 35) return { label: "Very Hot", color: "bg-red-100" };
      if (numValue < 18) return { label: "Cool", color: "bg-blue-100" };
      return { label: "Comfortable", color: "bg-green-50" };
    }
    if (sensorType === 'humidity') {
      if (numValue < 40) return { label: "Dry", color: "bg-yellow-100" };
      if (numValue > 80) return { label: "Very Humid", color: "bg-blue-100" };
      return { label: "Normal", color: "bg-cyan-50" };
    }
  };

  // Find profile
  const activeCropId = currentNode?.crop_type;
  const activeProfile = cropProfiles.find(profile => profile.crop_id === activeCropId);

  // Status Checkers
  const moistureStatus = getDynamicStatus('moisture', latest.moisture, activeProfile);
  const tempStatus = getDynamicStatus('temperature', latest.temperature, activeProfile);
  const phStatus = getDynamicStatus('ph', latest.ph, activeProfile);
  const nitrogenStatus = getDynamicStatus('nitrogen', latest.nitrogen, activeProfile);
  const phosphorusStatus = getDynamicStatus('phosphorus', latest.phosphorus, activeProfile);
  const potassiumStatus = getDynamicStatus('potassium', latest.potassium, activeProfile);

  const airTempStatus = getDynamicStatus('air_temperature', latest.air_temperature, null);
  const humidityStatus = getDynamicStatus('humidity', latest.humidity, null);

  const getConnectionStatus = (node) => {
    if (!node) return { color: "bg-gray-400", text: "Unknown" };

    if (node.last_seen && node.last_seen.seconds) {
      const lastSeenDate = new Date(node.last_seen.seconds * 1000);
      const now = new Date();
      const diffInMinutes = (now - lastSeenDate) / (1000 * 60);

      if (diffInMinutes > 5) {
        return { color: "bg-red-500", text: "Offline" };
      }
    }

    if (node.status === "online") return { color: "bg-green-500", text: "Online" };
    return { color: "bg-red-500", text: "Offline" };
  };

  if (currentView === 'settings') {
    return (
      <div className="min-h-screen bg-gray-50">
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
        <div className="p-4 md:p-8">
          <Settings />
        </div>
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
        
        {newNodeNotification && (
          <div className="fixed top-4 right-4 z-50 bg-green-600 text-white px-6 py-4 rounded-lg shadow-2xl animate-slide-in-right flex items-center gap-3">
            <CheckCircle className="text-green-200" size={24} />
            <div>
              <p className="font-bold">New Node Detected!</p>
              <p className="text-sm text-green-100">{newNodeNotification.nodeName} is now online</p>
            </div>
          </div>
        )}

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
            <button
              onClick={() => setCurrentView('settings')}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 flex items-center gap-2 transition-all"
            >
              <SettingsIcon size={18} />
              Settings
            </button>

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

        <div className="bg-white rounded-xl shadow-sm p-2 flex gap-2 overflow-x-auto">
          {Object.entries(nodes).map(([nodeId, nodeData]) => {
            const connectionStatus = getConnectionStatus(nodeData);
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
                    connectionStatus.text === 'Online' ? 'animate-pulse' : ''
                  }`}></span>
                  
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

        <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-100">
          <div className="flex justify-between items-center mb-4">
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

          <div className="mt-4 p-3 bg-green-50 rounded-lg border-2 border-green-200">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Sprout className="text-green-600" size={20} />
                <span className="text-sm font-medium text-gray-700">Assigned Crop:</span>
              </div>
              
              <select
                value={currentNode?.crop_type || 'default'}
                onChange={(e) => assignCropToNode(selectedNode, e.target.value)}
                disabled={assigningCrop}
                className="px-3 py-1.5 rounded-lg border-2 border-green-300 bg-white text-sm font-medium text-gray-700 hover:bg-green-50 focus:outline-none focus:ring-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                <option value="default">No specific crop (default thresholds)</option>
                {cropProfiles.map(profile => (
                  <option key={profile.crop_id} value={profile.crop_id}>
                    {profile.crop_name}
                  </option>
                ))}
              </select>
            </div>
            
            {assigningCrop && (
              <p className="text-xs text-green-600 animate-pulse flex items-center gap-1">
                <Activity size={12} className="animate-spin" />
                Updating crop assignment...
              </p>
            )}
            
            {currentNode?.crop_type && currentNode.crop_type !== 'default' && !assigningCrop && (
              <p className="text-xs text-green-600 flex items-center gap-1">
                <CheckCircle size={12} />
                Using crop-specific thresholds from uploaded documents
              </p>
            )}
            
            {(!currentNode?.crop_type || currentNode.crop_type === 'default') && !assigningCrop && (
              <p className="text-xs text-gray-500">
                Upload crop profiles in Settings to use specific thresholds
              </p>
            )}
          </div>
        </div>

        {/* 🌿 UPDATED: SOIL CONDITIONS SECTION (RAG Controlled) */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
          <h2 className="text-xl font-semibold mb-4 text-gray-700 flex items-center gap-2">
            <Sprout className="text-green-600" size={24} />
            Soil Conditions
            {activeCropId && activeCropId !== 'default' && (
              <span className="text-sm font-normal text-green-700 bg-green-100 px-3 py-0.5 rounded-full ml-2 capitalize">
                {activeCropId.replace('_', ' ')}
              </span>
            )}
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card icon={<Droplets className="text-blue-500" />} label="Soil Moisture" value={formatValue(latest.moisture, '%')} status={moistureStatus.label} color={moistureStatus.color} />
            <Card icon={<Thermometer className="text-orange-500" />} label="Soil Temperature" value={formatValue(latest.temperature, '°C')} status={tempStatus.label} color={tempStatus.color} />
            <Card icon={<Sprout className="text-green-500" />} label="Soil pH" value={latest.ph !== undefined && latest.ph !== null ? String(latest.ph) : "NO DATA"} status={phStatus.label} color={phStatus.color} />
            
            {/* Added NPK Cards directly into the RAG Grid using the imported Activity Icon */}
            <Card icon={<Activity className="text-blue-500" />} label="Nitrogen (N)" value={formatValue(latest.nitrogen, ' mg/kg')} status={nitrogenStatus.label} color={nitrogenStatus.color} />
            <Card icon={<Activity className="text-purple-500" />} label="Phosphorus (P)" value={formatValue(latest.phosphorus, ' mg/kg')} status={phosphorusStatus.label} color={phosphorusStatus.color} />
            <Card icon={<Activity className="text-green-500" />} label="Potassium (K)" value={formatValue(latest.potassium, ' mg/kg')} status={potassiumStatus.label} color={potassiumStatus.color} />
          </div>
        </div>

        {/* 🌤️ ENVIRONMENTAL CONDITIONS SECTION (Static Logic) */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
          <h2 className="text-xl font-semibold mb-4 text-gray-700 flex items-center gap-2">
            <Activity className="text-purple-600" size={24} />
            Environmental Conditions
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card
              icon={<Thermometer className="text-red-500" />}
              label="Air Temperature"
              value={formatValue(latest.air_temperature, '°C')}
              status={airTempStatus.label}
              color={airTempStatus.color}
            />
            <Card
              icon={<Droplets className="text-cyan-500" />}
              label="Air Humidity"
              value={formatValue(latest.humidity, '%')}
              status={humidityStatus.label}
              color={humidityStatus.color}
            />
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
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
      <div className="p-3 bg-gray-50 rounded-full shadow-sm">
        {icon}
      </div>
    </div>
  );
}

export default App;