// frontend/src/components/CropSelector.jsx
// Drop this anywhere in App.jsx next to each node tab

import { useState, useEffect, useRef } from 'react';
import { Leaf, ChevronDown, Check, Loader, BookOpen } from 'lucide-react';

const API_BASE = 'http://127.0.0.1:8000/api/v1';

export default function CropSelector({ nodeId, currentCrop, onCropChange }) {
  const [profiles, setProfiles] = useState([]);
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [assigning, setAssigning] = useState(false);
  const dropdownRef = useRef(null);

  // Load crop profiles on mount
  useEffect(() => {
    loadProfiles();
  }, []);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClick = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const loadProfiles = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/knowledge-library/`);
      const data = await res.json();
      setProfiles(data.crops || []);
    } catch (err) {
      console.error('Failed to load crop profiles:', err);
    } finally {
      setLoading(false);
    }
  };

  const assignCrop = async (cropId, cropName) => {
    if (cropId === currentCrop) {
      setIsOpen(false);
      return;
    }

    setAssigning(true);
    setIsOpen(false);

    try {
      const res = await fetch(`${API_BASE}/assign-crop/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ node_id: nodeId, crop_type: cropId })
      });

      const data = await res.json();

      if (res.ok) {
        onCropChange?.(cropId, cropName, data.thresholds);
      } else {
        console.error('Assignment failed:', data.error);
      }
    } catch (err) {
      console.error('Error assigning crop:', err);
    } finally {
      setAssigning(false);
    }
  };

  // Get display name for current crop
  const currentProfile = profiles.find(p => p.crop_id === currentCrop);
  const displayName = currentProfile?.crop_name || (currentCrop
    ? currentCrop.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
    : 'Select Crop');

  const hasProfiles = profiles.length > 0;

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Trigger Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={assigning}
        className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-sm font-medium transition-all ${
          currentCrop && currentCrop !== 'default'
            ? 'bg-green-50 border-green-300 text-green-700 hover:bg-green-100'
            : 'bg-gray-50 border-gray-300 text-gray-500 hover:bg-gray-100'
        } ${assigning ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
      >
        {assigning ? (
          <Loader className="animate-spin" size={14} />
        ) : (
          <Leaf size={14} />
        )}
        <span>{assigning ? 'Switching...' : displayName}</span>
        {!assigning && <ChevronDown size={14} className={`transition-transform ${isOpen ? 'rotate-180' : ''}`} />}
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute top-full left-0 mt-1 w-64 bg-white rounded-xl shadow-xl border border-gray-200 z-50 overflow-hidden">
          <div className="px-3 py-2 border-b border-gray-100 flex items-center justify-between">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
              Select Crop Profile
            </p>
            {loading && <Loader className="animate-spin text-gray-400" size={12} />}
          </div>

          <div className="max-h-60 overflow-y-auto">
            {!hasProfiles ? (
              <div className="px-4 py-6 text-center">
                <BookOpen className="mx-auto mb-2 text-gray-300" size={28} />
                <p className="text-xs text-gray-500 font-medium">No crop profiles yet</p>
                <p className="text-xs text-gray-400 mt-1">
                  Go to Settings → Upload Document to build your library
                </p>
              </div>
            ) : (
              <>
                {/* No crop option */}
                <button
                  onClick={() => assignCrop('default', 'Default')}
                  className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-gray-50 transition-colors text-left"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-lg">⚙️</span>
                    <div>
                      <p className="text-sm font-medium text-gray-700">Default</p>
                      <p className="text-xs text-gray-400">Use fallback thresholds</p>
                    </div>
                  </div>
                  {(currentCrop === 'default' || !currentCrop) && (
                    <Check size={14} className="text-green-600" />
                  )}
                </button>

                <div className="border-t border-gray-100" />

                {/* Crop profiles */}
                {profiles.map(profile => {
                  const isActive = profile.crop_id === currentCrop;
                  const hasThresholds = profile.thresholds &&
                    Object.values(profile.thresholds).some(v => v != null);

                  return (
                    <button
                      key={profile.crop_id}
                      onClick={() => assignCrop(profile.crop_id, profile.crop_name)}
                      className={`w-full flex items-center justify-between px-4 py-2.5 transition-colors text-left ${
                        isActive ? 'bg-green-50' : 'hover:bg-gray-50'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <span className="text-lg">🌱</span>
                        <div>
                          <p className={`text-sm font-medium ${
                            isActive ? 'text-green-700' : 'text-gray-700'
                          }`}>
                            {profile.crop_name}
                          </p>
                          <p className="text-xs text-gray-400">
                            {profile.document_count} doc{profile.document_count !== 1 ? 's' : ''}
                            {hasThresholds
                              ? ' • Thresholds ready ✓'
                              : ' • No thresholds yet'
                            }
                          </p>
                        </div>
                      </div>
                      {isActive && <Check size={14} className="text-green-600" />}
                    </button>
                  );
                })}
              </>
            )}
          </div>

          {/* Footer link to settings */}
          <div className="border-t border-gray-100 px-3 py-2">
            <p className="text-xs text-gray-400 text-center">
              Add crops in{' '}
              <span className="text-green-600 font-medium">Settings → Knowledge Library</span>
            </p>
          </div>
        </div>
      )}
    </div>
  );
}