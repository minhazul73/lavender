import React from 'react';
import type { UserItem, GroupCategoryItem } from '../../api/types';
import { Search, Layers } from 'lucide-react';

export type GroupFilterType = 'all' | 'Privileged' | 'Hardware' | 'Services' | 'System';

function getUsername(u: UserItem): string {
  return u.name || u.username || '';
}

export interface GroupsTabProps {
  groupFilter: GroupFilterType;
  setGroupFilter: (filter: GroupFilterType) => void;
  groupCounts: { all: number; priv: number; hw: number; serv: number; sys: number };
  groupSearch: string;
  setGroupSearch: (search: string) => void;
  filteredGroups: GroupCategoryItem[];
  humanUsers: UserItem[];
  primaryHumanUser?: UserItem;
  handleOpenEditGroups: (user: UserItem) => void;
}

export const GroupsTab: React.FC<GroupsTabProps> = ({
  groupFilter,
  setGroupFilter,
  groupCounts,
  groupSearch,
  setGroupSearch,
  filteredGroups,
  humanUsers,
  primaryHumanUser,
  handleOpenEditGroups,
}) => {
  return (
    <div className="groups-tab-container">
      {/* Filter Pills Bar & Search Toolbar */}
      <div className="groups-toolbar">
        <div className="filter-pills-bar">
          <button
            className={`filter-pill ${groupFilter === 'all' ? 'active' : ''}`}
            onClick={() => setGroupFilter('all')}
          >
            All Groups ({groupCounts.all})
          </button>
          <button
            className={`filter-pill ${groupFilter === 'Privileged' ? 'active' : ''}`}
            onClick={() => setGroupFilter('Privileged')}
          >
            Privileged ({groupCounts.priv})
          </button>
          <button
            className={`filter-pill ${groupFilter === 'Hardware' ? 'active' : ''}`}
            onClick={() => setGroupFilter('Hardware')}
          >
            Phone & Hardware ({groupCounts.hw})
          </button>
          <button
            className={`filter-pill ${groupFilter === 'Services' ? 'active' : ''}`}
            onClick={() => setGroupFilter('Services')}
          >
            Services ({groupCounts.serv})
          </button>
          <button
            className={`filter-pill ${groupFilter === 'System' ? 'active' : ''}`}
            onClick={() => setGroupFilter('System')}
          >
            System ({groupCounts.sys})
          </button>
        </div>

        <div className="groups-search-wrap">
          <Search
            size={14}
            className="groups-search-icon"
          />
          <input
            type="search"
            className="input groups-search-input"
            placeholder="Search groups (e.g. wheel, audio, docker)..."
            value={groupSearch}
            onChange={(e) => setGroupSearch(e.target.value)}
          />
        </div>
      </div>

      {/* Groups Table Card */}
      <div className="card groups-card">
        <div className="card-body groups-card-body">
          <div className="groups-table-wrap">
            <table className="table groups-table">
              <thead>
                <tr>
                  <th className="col-group-name">Group Name</th>
                  <th className="col-group-gid">GID</th>
                  <th className="col-group-cat">Category</th>
                  <th className="col-group-desc">Subsystem / Permission</th>
                  <th className="col-group-members">Members</th>
                  <th className="col-group-actions">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredGroups.length === 0 ? (
                  <tr className="groups-empty-row">
                    <td colSpan={6} className="groups-empty-cell">
                      <div className="groups-empty-content">
                        <Layers size={18} className="groups-empty-icon" />
                        <span>No groups match current filter</span>
                      </div>
                    </td>
                  </tr>
                ) : (
                  filteredGroups.map((g) => {
                    let catBadge = <span className="badge badge-neutral">System</span>;
                    if (g.category === 'Privileged') {
                      catBadge = <span className="badge badge-lavender">Privileged</span>;
                    } else if (g.category === 'Hardware') {
                      catBadge = <span className="badge badge-success">Hardware</span>;
                    } else if (g.category === 'Services') {
                      catBadge = <span className="badge badge-services">Services</span>;
                    }

                    return (
                      <tr key={g.name} className="group-item-row">
                        <td className="group-cell-name font-mono">
                          <span className="group-name-text">{g.name}</span>
                        </td>
                        <td className="group-cell-gid font-mono">
                          <span className="group-gid-badge">
                            <span className="group-gid-prefix">GID </span>
                            {g.gid}
                          </span>
                        </td>
                        <td className="group-cell-cat">{catBadge}</td>
                        <td className="group-cell-desc">
                          <span className="group-meta-label">Subsystem / Permission</span>
                          <span className="group-desc-text">{g.description}</span>
                        </td>
                        <td className="group-cell-members">
                          <span className="group-meta-label">Members</span>
                          <div className="group-members-wrap">
                            {g.members && g.members.length > 0 ? (
                              g.members.map((m) => {
                                const isHuman = humanUsers.some((u) => getUsername(u) === m);
                                return (
                                  <span
                                    key={m}
                                    className={`group-tag ${isHuman ? 'tag-wheel' : ''}`}
                                  >
                                    {m}
                                  </span>
                                );
                              })
                            ) : (
                              <span className="group-no-members">—</span>
                            )}
                          </div>
                        </td>
                        <td className="group-cell-actions">
                          {primaryHumanUser && (
                            <button
                              className="btn btn-xs btn-ghost group-action-btn"
                              onClick={() => handleOpenEditGroups(primaryHumanUser)}
                              title={`Edit group assignments for ${getUsername(primaryHumanUser)}`}
                            >
                              <span>Edit</span>
                            </button>
                          )}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
