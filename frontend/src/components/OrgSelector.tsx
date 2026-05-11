import React, { useState, useEffect, useRef } from 'react';
import { ChevronDownIcon, BuildingOfficeIcon, FolderIcon } from '@heroicons/react/24/outline';

const API_BASE = process.env.REACT_APP_API_URL || 'http://127.0.0.1:9899/api/v1';

interface OrgOption {
  id: number;
  name: string;
  slug: string;
  plan: string;
}

interface ProjectOption {
  id: number;
  name: string;
  project_type: string;
}

async function apiRequest<T>(path: string): Promise<T> {
  const token = localStorage.getItem('access_token');
  const resp = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
  if (!resp.ok) throw new Error(`API ${resp.status}`);
  return resp.json();
}

interface OrgSelectorProps {
  onOrgChange?: (org: OrgOption | null) => void;
  onProjectChange?: (project: ProjectOption | null) => void;
}

const OrgSelector: React.FC<OrgSelectorProps> = ({ onOrgChange, onProjectChange }) => {
  const [orgs, setOrgs] = useState<OrgOption[]>([]);
  const [projects, setProjects] = useState<ProjectOption[]>([]);
  const [selectedOrg, setSelectedOrg] = useState<OrgOption | null>(null);
  const [selectedProject, setSelectedProject] = useState<ProjectOption | null>(null);
  const [isOrgOpen, setIsOrgOpen] = useState(false);
  const [isProjectOpen, setIsProjectOpen] = useState(false);
  const orgRef = useRef<HTMLDivElement>(null);
  const projectRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    apiRequest<{ items: OrgOption[] }>('/org/')
      .then(d => setOrgs(d.items))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!selectedOrg) {
      setProjects([]);
      setSelectedProject(null);
      return;
    }
    apiRequest<{ items: ProjectOption[] }>(`/org/${selectedOrg.id}/projects`)
      .then(d => setProjects(d.items))
      .catch(() => setProjects([]));
  }, [selectedOrg]);

  // Close dropdowns on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (orgRef.current && !orgRef.current.contains(e.target as Node)) setIsOrgOpen(false);
      if (projectRef.current && !projectRef.current.contains(e.target as Node)) setIsProjectOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const selectOrg = (org: OrgOption) => {
    setSelectedOrg(org);
    setSelectedProject(null);
    setIsOrgOpen(false);
    onOrgChange?.(org);
    onProjectChange?.(null);
  };

  const selectProject = (project: ProjectOption) => {
    setSelectedProject(project);
    setIsProjectOpen(false);
    onProjectChange?.(project);
  };

  return (
    <div className="flex items-center gap-2">
      {/* Org selector */}
      <div ref={orgRef} className="relative">
        <button
          onClick={() => setIsOrgOpen(o => !o)}
          className="flex items-center gap-2 px-3 py-1.5 text-sm border border-gray-300 rounded-lg bg-white hover:bg-gray-50 min-w-[140px]"
        >
          <BuildingOfficeIcon className="h-4 w-4 text-gray-400 flex-shrink-0" />
          <span className="flex-1 text-left truncate">
            {selectedOrg ? selectedOrg.name : 'Select org…'}
          </span>
          <ChevronDownIcon className="h-3.5 w-3.5 text-gray-400 flex-shrink-0" />
        </button>
        {isOrgOpen && (
          <div className="absolute top-full left-0 mt-1 w-56 bg-white border border-gray-200 rounded-xl shadow-lg z-50 py-1">
            {orgs.length === 0 ? (
              <p className="px-4 py-2 text-sm text-gray-400">No organizations</p>
            ) : (
              orgs.map(org => (
                <button
                  key={org.id}
                  onClick={() => selectOrg(org)}
                  className={`w-full text-left px-4 py-2 text-sm hover:bg-gray-50 flex items-center gap-2 ${
                    selectedOrg?.id === org.id ? 'text-indigo-600 bg-indigo-50' : 'text-gray-700'
                  }`}
                >
                  <BuildingOfficeIcon className="h-4 w-4 flex-shrink-0" />
                  <span className="flex-1 truncate">{org.name}</span>
                  <span className="text-xs text-gray-400 capitalize">{org.plan}</span>
                </button>
              ))
            )}
            <div className="border-t border-gray-100 mt-1 pt-1">
              <a
                href="/organizations"
                className="block px-4 py-2 text-xs text-indigo-600 hover:bg-indigo-50"
              >
                Manage organizations →
              </a>
            </div>
          </div>
        )}
      </div>

      {/* Project selector */}
      {selectedOrg && (
        <div ref={projectRef} className="relative">
          <button
            onClick={() => setIsProjectOpen(o => !o)}
            className="flex items-center gap-2 px-3 py-1.5 text-sm border border-gray-300 rounded-lg bg-white hover:bg-gray-50 min-w-[140px]"
          >
            <FolderIcon className="h-4 w-4 text-gray-400 flex-shrink-0" />
            <span className="flex-1 text-left truncate">
              {selectedProject ? selectedProject.name : 'Select project…'}
            </span>
            <ChevronDownIcon className="h-3.5 w-3.5 text-gray-400 flex-shrink-0" />
          </button>
          {isProjectOpen && (
            <div className="absolute top-full left-0 mt-1 w-56 bg-white border border-gray-200 rounded-xl shadow-lg z-50 py-1">
              {projects.length === 0 ? (
                <p className="px-4 py-2 text-sm text-gray-400">No projects yet</p>
              ) : (
                projects.map(project => (
                  <button
                    key={project.id}
                    onClick={() => selectProject(project)}
                    className={`w-full text-left px-4 py-2 text-sm hover:bg-gray-50 flex items-center gap-2 ${
                      selectedProject?.id === project.id ? 'text-emerald-600 bg-emerald-50' : 'text-gray-700'
                    }`}
                  >
                    <FolderIcon className="h-4 w-4 flex-shrink-0" />
                    <span className="flex-1 truncate">{project.name}</span>
                    <span className="text-xs text-gray-400 capitalize">{project.project_type}</span>
                  </button>
                ))
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default OrgSelector;
