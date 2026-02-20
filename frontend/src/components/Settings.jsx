// frontend/src/components/Settings.jsx
import { useState, useEffect } from 'react';
import {
  Book, Upload, Trash2, Search, FileText, AlertCircle,
  CheckCircle, X, Loader, Globe, Leaf, ChevronDown,
  Plus, BarChart2, RefreshCw, Info
} from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';

const API_BASE = 'http://127.0.0.1:8000/api/v1';

export default function Settings() {
  const { language, setLanguage, t } = useLanguage();

  // ── State ──
  const [activeTab, setActiveTab] = useState('library'); // 'library' | 'upload' | 'search' | 'language'
  const [cropProfiles, setCropProfiles] = useState([]);
  const [selectedProfile, setSelectedProfile] = useState(null);
  const [nodes, setNodes] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [notification, setNotification] = useState(null);
  const [loadingLibrary, setLoadingLibrary] = useState(true);
  const [assigningCrop, setAssigningCrop] = useState({});

  useEffect(() => {
    loadCropProfiles();
    loadNodes();
  }, []);

  // ── Data Fetching ──
  const loadCropProfiles = async () => {
    setLoadingLibrary(true);
    try {
      const res = await fetch(`${API_BASE}/knowledge-library/`);
      const data = await res.json();
      setCropProfiles(data.crops || []);
    } catch (err) {
      showNotification('error', 'Failed to load Knowledge Library');
    } finally {
      setLoadingLibrary(false);
    }
  };

  const loadNodes = async () => {
    // Nodes come from Firebase via App.jsx, but we can also fetch from the backend
    // For simplicity, we'll let the user select node manually here
    // This can be connected to Firebase directly if needed
  };

  const showNotification = (type, message) => {
    setNotification({ type, message });
    setTimeout(() => setNotification(null), 5000);
  };

  // ── Upload Document ──
  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const validTypes = ['.pdf', '.docx', '.txt'];
    const fileExt = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    if (!validTypes.includes(fileExt)) {
      showNotification('error', 'Please upload PDF, DOCX, or TXT files only');
      return;
    }
    document.getElementById('upload-modal').classList.remove('hidden');
    window.pendingFile = file;
  };

  const confirmUpload = async () => {
    const cropType = document.getElementById('crop-type-input').value.trim();
    const description = document.getElementById('description-input').value.trim();

    if (!cropType) {
      showNotification('error', 'Crop type is required to build the Knowledge Library');
      return;
    }

    if (!window.pendingFile) return;

    setUploading(true);
    closeModal();

    const formData = new FormData();
    formData.append('file', window.pendingFile);
    formData.append('document_name', window.pendingFile.name);
    formData.append('crop_type', cropType);
    formData.append('description', description);

    try {
      const res = await fetch(`${API_BASE}/upload-document/`, {
        method: 'POST',
        body: formData
      });
      const data = await res.json();

      if (res.ok) {
        showNotification(
          'success',
          `"${cropType.charAt(0).toUpperCase() + cropType.slice(1)}" profile updated! Created ${data.chunks_created} knowledge chunks.`
        );
        loadCropProfiles(); // Refresh library
        setActiveTab('library'); // Switch to library view
      } else {
        showNotification('error', data.error || 'Upload failed');
      }
    } catch (err) {
      showNotification('error', `Upload error: ${err.message}`);
    } finally {
      setUploading(false);
    }
  };

  const closeModal = () => {
    document.getElementById('upload-modal').classList.add('hidden');
    document.getElementById('crop-type-input').value = '';
    document.getElementById('description-input').value = '';
    window.pendingFile = null;
  };

  // ── Assign Crop to Node ──
  const assignCropToNode = async (nodeId, cropType) => {
    setAssigningCrop(prev => ({ ...prev, [nodeId]: true }));
    try {
      const res = await fetch(`${API_BASE}/assign-crop/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ node_id: nodeId, crop_type: cropType })
      });
      const data = await res.json();
      if (res.ok) {
        showNotification('success', `Node switched to "${cropType}" profile!`);
      } else {
        showNotification('error', data.error || 'Assignment failed');
      }
    } catch (err) {
      showNotification('error', `Error: ${err.message}`);
    } finally {
      setAssigningCrop(prev => ({ ...prev, [nodeId]: false }));
    }
  };

  // ── Delete Crop Profile ──
  const deleteCropProfile = async (cropId, cropName) => {
    if (!confirm(`Delete "${cropName}" profile? This will remove all associated thresholds and knowledge.`)) return;
    try {
      const res = await fetch(`${API_BASE}/knowledge-library/${cropId}/`, { method: 'DELETE' });
      if (res.ok) {
        showNotification('success', `"${cropName}" profile deleted`);
        loadCropProfiles();
        if (selectedProfile?.crop_id === cropId) setSelectedProfile(null);
      }
    } catch (err) {
      showNotification('error', `Delete failed: ${err.message}`);
    }
  };

  // ── Search ──
  const searchKnowledge = async () => {
    if (!searchQuery.trim()) return;
    setSearching(true);
    try {
      const res = await fetch(`${API_BASE}/search-knowledge/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: searchQuery, n_results: 5 })
      });
      const data = await res.json();
      setSearchResults(data.results || []);
    } catch (err) {
      showNotification('error', 'Search failed');
    } finally {
      setSearching(false);
    }
  };

  // ── Threshold Display Helper ──
  const ThresholdBadge = ({ label, min, max, unit }) => {
    if (min == null && max == null) return null;
    return (
      <div className="bg-gray-50 rounded-lg px-3 py-2 text-center">
        <p className="text-xs text-gray-500 mb-1">{label}</p>
        <p className="text-sm font-bold text-gray-800">
          {min ?? '?'} – {max ?? '?'}
          <span className="text-xs font-normal text-gray-500 ml-1">{unit}</span>
        </p>
      </div>
    );
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">

      {/* Notification */}
      {notification && (
        <div className={`fixed top-4 right-4 z-50 px-6 py-4 rounded-xl shadow-2xl flex items-center gap-3 ${
          notification.type === 'success' ? 'bg-green-600 text-white' : 'bg-red-600 text-white'
        }`}>
          {notification.type === 'success' ? <CheckCircle size={22} /> : <AlertCircle size={22} />}
          <p className="font-medium">{notification.message}</p>
          <button onClick={() => setNotification(null)}><X size={16} /></button>
        </div>
      )}

      {/* Header */}
      <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
        <h1 className="text-2xl font-bold text-gray-800 flex items-center gap-3">
          <Book className="text-green-600" size={30} />
          Settings
        </h1>
        <p className="text-gray-500 mt-1 text-sm">
          Manage your Knowledge Library, language preferences, and node assignments
        </p>
      </div>

      {/* Tab Navigation */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="flex border-b border-gray-200">
          {[
            { id: 'library', icon: <Book size={16} />, label: 'Knowledge Library' },
            { id: 'upload', icon: <Upload size={16} />, label: 'Upload Document' },
            { id: 'search', icon: <Search size={16} />, label: 'Search Knowledge' },
            { id: 'language', icon: <Globe size={16} />, label: 'Language' },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-5 py-4 text-sm font-medium border-b-2 transition-all ${
                activeTab === tab.id
                  ? 'border-green-600 text-green-700 bg-green-50'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-50'
              }`}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>

        {/* ── TAB: KNOWLEDGE LIBRARY ── */}
        {activeTab === 'library' && (
          <div className="p-6">
            <div className="flex justify-between items-center mb-6">
              <div>
                <h2 className="text-lg font-bold text-gray-800">Crop Profile Library</h2>
                <p className="text-sm text-gray-500 mt-1">
                  {cropProfiles.length} crop profile{cropProfiles.length !== 1 ? 's' : ''} stored permanently
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={loadCropProfiles}
                  className="p-2 text-gray-500 hover:bg-gray-100 rounded-lg"
                  title="Refresh"
                >
                  <RefreshCw size={18} />
                </button>
                <button
                  onClick={() => setActiveTab('upload')}
                  className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 flex items-center gap-2 text-sm"
                >
                  <Plus size={16} />
                  Add Crop Profile
                </button>
              </div>
            </div>

            {loadingLibrary ? (
              <div className="flex items-center justify-center py-16">
                <Loader className="animate-spin text-green-600" size={32} />
                <span className="ml-3 text-gray-500">Loading library...</span>
              </div>
            ) : cropProfiles.length === 0 ? (
              <div className="text-center py-16 bg-gray-50 rounded-xl border-2 border-dashed border-gray-300">
                <Leaf className="mx-auto mb-4 text-gray-400" size={48} />
                <p className="text-gray-600 font-semibold">No Crop Profiles Yet</p>
                <p className="text-sm text-gray-400 mt-2 mb-4">
                  Upload a farming document to create your first crop profile
                </p>
                <button
                  onClick={() => setActiveTab('upload')}
                  className="bg-green-600 text-white px-6 py-2 rounded-lg hover:bg-green-700 text-sm"
                >
                  Upload First Document
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                {cropProfiles.map(profile => (
                  <CropProfileCard
                    key={profile.crop_id}
                    profile={profile}
                    isSelected={selectedProfile?.crop_id === profile.crop_id}
                    onSelect={() => setSelectedProfile(
                      selectedProfile?.crop_id === profile.crop_id ? null : profile
                    )}
                    onDelete={() => deleteCropProfile(profile.crop_id, profile.crop_name)}
                  />
                ))}
              </div>
            )}

            {/* Selected Profile Detail */}
            {selectedProfile && (
              <div className="mt-6 bg-green-50 border border-green-200 rounded-xl p-6">
                <div className="flex justify-between items-start mb-4">
                  <h3 className="text-lg font-bold text-green-800 flex items-center gap-2">
                    <Leaf size={20} />
                    {selectedProfile.crop_name} — Threshold Reference
                  </h3>
                  <button
                    onClick={() => setSelectedProfile(null)}
                    className="text-green-600 hover:bg-green-100 p-1 rounded"
                  >
                    <X size={16} />
                  </button>
                </div>

                {selectedProfile.thresholds && Object.keys(selectedProfile.thresholds).length > 0 ? (
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <ThresholdBadge
                      label="Soil Moisture"
                      min={selectedProfile.thresholds.moisture_min}
                      max={selectedProfile.thresholds.moisture_max}
                      unit="%"
                    />
                    <ThresholdBadge
                      label="Soil pH"
                      min={selectedProfile.thresholds.ph_min}
                      max={selectedProfile.thresholds.ph_max}
                      unit="pH"
                    />
                    <ThresholdBadge
                      label="Temperature"
                      min={selectedProfile.thresholds.temp_min}
                      max={selectedProfile.thresholds.temp_max}
                      unit="°C"
                    />
                    <ThresholdBadge
                      label="Humidity"
                      min={selectedProfile.thresholds.humidity_min}
                      max={selectedProfile.thresholds.humidity_max}
                      unit="%"
                    />
                    <ThresholdBadge
                      label="Nitrogen (N)"
                      min={selectedProfile.thresholds.nitrogen_min}
                      max={selectedProfile.thresholds.nitrogen_max}
                      unit="mg/kg"
                    />
                    <ThresholdBadge
                      label="Phosphorus (P)"
                      min={selectedProfile.thresholds.phosphorus_min}
                      max={selectedProfile.thresholds.phosphorus_max}
                      unit="mg/kg"
                    />
                    <ThresholdBadge
                      label="Potassium (K)"
                      min={selectedProfile.thresholds.potassium_min}
                      max={selectedProfile.thresholds.potassium_max}
                      unit="mg/kg"
                    />
                  </div>
                ) : (
                  <p className="text-sm text-green-700 bg-green-100 rounded-lg p-3 flex items-center gap-2">
                    <Info size={16} />
                    No thresholds extracted yet. Upload a document with specific crop requirements.
                  </p>
                )}

                {/* Documents in this profile */}
                {selectedProfile.documents?.length > 0 && (
                  <div className="mt-4">
                    <p className="text-sm font-semibold text-green-800 mb-2">
                      Source Documents ({selectedProfile.documents.length})
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {selectedProfile.documents.map((doc, i) => (
                        <span key={i} className="bg-white text-green-700 text-xs px-3 py-1 rounded-full border border-green-200 flex items-center gap-1">
                          <FileText size={12} />
                          {doc}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* ── TAB: UPLOAD ── */}
        {activeTab === 'upload' && (
          <div className="p-6 space-y-6">
            <div>
              <h2 className="text-lg font-bold text-gray-800">Upload Agricultural Document</h2>
              <p className="text-sm text-gray-500 mt-1">
                Upload a document to create or update a crop profile in the Knowledge Library
              </p>
            </div>

            <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
              <p className="text-sm font-semibold text-blue-800 mb-2 flex items-center gap-2">
                <Info size={16} />
                How the Knowledge Library works:
              </p>
              <ul className="text-sm text-blue-700 space-y-1">
                <li>• Upload "tomato_guide.pdf" → Creates permanent "Tomato" profile</li>
                <li>• Upload "rice_manual.pdf" → Creates permanent "Rice" profile</li>
                <li>• Switch crops instantly using the dropdown on the dashboard</li>
                <li>• Alerts and AI chatbot both use the selected crop's thresholds</li>
                <li>• Upload more documents to enrich any existing profile</li>
              </ul>
            </div>

            <label className={`flex flex-col items-center justify-center border-2 border-dashed border-gray-300 rounded-xl p-12 cursor-pointer hover:border-green-500 hover:bg-green-50 transition-all ${
              uploading ? 'opacity-50 cursor-not-allowed' : ''
            }`}>
              {uploading ? (
                <>
                  <Loader className="animate-spin text-green-600 mb-3" size={40} />
                  <p className="text-green-700 font-semibold">Processing document...</p>
                  <p className="text-xs text-gray-500 mt-1">Extracting thresholds with AI...</p>
                </>
              ) : (
                <>
                  <Upload className="text-gray-400 mb-3" size={40} />
                  <p className="text-gray-700 font-semibold">Click to upload document</p>
                  <p className="text-xs text-gray-400 mt-1">PDF, DOCX, TXT supported</p>
                </>
              )}
              <input
                type="file"
                accept=".pdf,.docx,.txt"
                onChange={handleFileUpload}
                disabled={uploading}
                className="hidden"
              />
            </label>

            {/* Existing Profiles Quick View */}
            {cropProfiles.length > 0 && (
              <div>
                <p className="text-sm font-semibold text-gray-700 mb-3">
                  Existing profiles (you can add more documents to any):
                </p>
                <div className="flex flex-wrap gap-2">
                  {cropProfiles.map(p => (
                    <span key={p.crop_id} className="bg-green-100 text-green-700 text-sm px-3 py-1 rounded-full flex items-center gap-1">
                      <Leaf size={13} />
                      {p.crop_name}
                      <span className="text-xs text-green-500">({p.document_count} docs)</span>
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── TAB: SEARCH ── */}
        {activeTab === 'search' && (
          <div className="p-6 space-y-4">
            <div>
              <h2 className="text-lg font-bold text-gray-800">Search Knowledge Base</h2>
              <p className="text-sm text-gray-500 mt-1">
                Test what the AI knows from uploaded documents
              </p>
            </div>

            <div className="flex gap-2">
              <input
                className="flex-1 border border-gray-300 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-green-500"
                placeholder="e.g., 'What are optimal pH conditions for tomatoes?'"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && searchKnowledge()}
              />
              <button
                onClick={searchKnowledge}
                disabled={searching || !searchQuery.trim()}
                className="bg-green-600 text-white px-6 py-3 rounded-lg hover:bg-green-700 disabled:bg-gray-400 flex items-center gap-2"
              >
                {searching ? <Loader className="animate-spin" size={18} /> : <Search size={18} />}
                {searching ? 'Searching...' : 'Search'}
              </button>
            </div>

            {searchResults.length > 0 && (
              <div className="space-y-3">
                <p className="font-medium text-gray-700 text-sm">
                  Found {searchResults.length} relevant chunks:
                </p>
                {searchResults.map((result, idx) => (
                  <div key={idx} className="bg-gray-50 p-4 rounded-xl border border-gray-200">
                    <p className="text-sm text-gray-700 mb-3">{result.text}</p>
                    <div className="flex gap-3 text-xs text-gray-400">
                      <span className="flex items-center gap-1">
                        <FileText size={12} />
                        {result.metadata.document_name}
                      </span>
                      {result.metadata.crop_type && (
                        <span className="flex items-center gap-1">
                          <Leaf size={12} />
                          {result.metadata.crop_type}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ── TAB: LANGUAGE ── */}
        {activeTab === 'language' && (
          <div className="p-6 space-y-4">
            <div>
              <h2 className="text-lg font-bold text-gray-800 flex items-center gap-2">
                <Globe className="text-blue-600" size={22} />
                Language Settings
              </h2>
              <p className="text-sm text-gray-500 mt-1">
                Select your preferred language for the dashboard and AI chatbot
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4 max-w-sm">
              <button
                onClick={() => setLanguage('en')}
                className={`p-5 rounded-xl border-2 font-medium transition-all ${
                  language === 'en'
                    ? 'border-blue-600 bg-blue-50 text-blue-700'
                    : 'border-gray-200 text-gray-600 hover:border-gray-300'
                }`}
              >
                <div className="text-3xl mb-2">🇺🇸</div>
                English
              </button>
              <button
                onClick={() => setLanguage('fil')}
                className={`p-5 rounded-xl border-2 font-medium transition-all ${
                  language === 'fil'
                    ? 'border-blue-600 bg-blue-50 text-blue-700'
                    : 'border-gray-200 text-gray-600 hover:border-gray-300'
                }`}
              >
                <div className="text-3xl mb-2">🇵🇭</div>
                Filipino
              </button>
            </div>

            <div className="bg-blue-50 rounded-xl p-4 max-w-sm">
              <p className="text-xs text-blue-700">
                The AI chatbot will also respond in your selected language automatically.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Upload Modal */}
      <div id="upload-modal" className="hidden fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center">
        <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full mx-4">
          <div className="p-6 border-b border-gray-200">
            <h3 className="text-xl font-bold text-gray-800">Add to Knowledge Library</h3>
            <p className="text-sm text-gray-500 mt-1">
              This document will create or update a crop profile
            </p>
          </div>

          <div className="p-6 space-y-4">
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Crop Type <span className="text-red-500">*</span>
              </label>
              <input
                id="crop-type-input"
                type="text"
                placeholder="e.g., tomato, rice, corn, lettuce"
                className="w-full border border-gray-300 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-green-500"
              />
              <p className="text-xs text-gray-400 mt-1">
                Use the same name to add more docs to an existing profile
              </p>
            </div>

            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">
                Description (Optional)
              </label>
              <textarea
                id="description-input"
                placeholder="e.g., Official growing guide for tropical tomato cultivation"
                rows="2"
                className="w-full border border-gray-300 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-green-500 resize-none"
              />
            </div>

            {/* Quick select existing crop */}
            {cropProfiles.length > 0 && (
              <div>
                <p className="text-xs text-gray-500 mb-2">Or add to existing profile:</p>
                <div className="flex flex-wrap gap-2">
                  {cropProfiles.map(p => (
                    <button
                      key={p.crop_id}
                      onClick={() => {
                        document.getElementById('crop-type-input').value = p.crop_id;
                        document.getElementById('description-input').value = p.description || '';
                      }}
                      className="bg-gray-100 hover:bg-green-100 text-gray-700 hover:text-green-700 text-xs px-3 py-1 rounded-full border border-gray-200 hover:border-green-300 transition-all"
                    >
                      {p.crop_name}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="p-6 border-t border-gray-200 flex gap-3">
            <button
              onClick={confirmUpload}
              className="flex-1 bg-green-600 text-white px-4 py-3 rounded-lg hover:bg-green-700 font-semibold"
            >
              Upload & Save to Library
            </button>
            <button
              onClick={closeModal}
              className="px-5 py-3 border border-gray-300 rounded-lg hover:bg-gray-50"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Sub-component: Crop Profile Card ──
function CropProfileCard({ profile, isSelected, onSelect, onDelete }) {
  const hasThresholds = profile.thresholds && Object.values(profile.thresholds).some(v => v != null);

  return (
    <div
      onClick={onSelect}
      className={`border-2 rounded-xl p-4 cursor-pointer transition-all hover:shadow-md ${
        isSelected
          ? 'border-green-500 bg-green-50 shadow-md'
          : 'border-gray-200 bg-white hover:border-gray-300'
      }`}
    >
      <div className="flex justify-between items-start mb-3">
        <div className="flex items-center gap-2">
          <div className={`w-10 h-10 rounded-full flex items-center justify-center text-xl ${
            isSelected ? 'bg-green-200' : 'bg-gray-100'
          }`}>
            🌱
          </div>
          <div>
            <h3 className="font-bold text-gray-800">{profile.crop_name}</h3>
            <p className="text-xs text-gray-400">
              {profile.document_count} document{profile.document_count !== 1 ? 's' : ''}
            </p>
          </div>
        </div>
        <button
          onClick={(e) => { e.stopPropagation(); onDelete(); }}
          className="text-red-400 hover:bg-red-50 p-1.5 rounded-lg transition-colors"
          title="Delete profile"
        >
          <Trash2 size={15} />
        </button>
      </div>

      {profile.description && (
        <p className="text-xs text-gray-500 mb-3 line-clamp-2">{profile.description}</p>
      )}

      <div className="flex items-center justify-between">
        <div className="flex gap-1">
          {hasThresholds ? (
            <span className="bg-green-100 text-green-700 text-xs px-2 py-0.5 rounded-full flex items-center gap-1">
              <CheckCircle size={11} />
              Thresholds ready
            </span>
          ) : (
            <span className="bg-yellow-100 text-yellow-700 text-xs px-2 py-0.5 rounded-full flex items-center gap-1">
              <AlertCircle size={11} />
              No thresholds
            </span>
          )}
        </div>
        <span className="text-xs text-gray-400">
          {isSelected ? 'Click to close ▲' : 'Click to view ▼'}
        </span>
      </div>
    </div>
  );
}