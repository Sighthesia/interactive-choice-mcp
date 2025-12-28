# Delta Spec: choice-orchestration

## ADDED Requirements

### Requirement: REQ-PERSIST-01 Session Persistence
The system MUST persist completed sessions to local storage.

#### Scenario: Session saved after completion
- **Given**: A web or terminal session is completed
- **When**: The session result is finalized
- **Then**: The session data is written to disk

### Requirement: REQ-PERSIST-02 Historical Session Loading
The system MUST load historical sessions on server startup.

#### Scenario: Server restart preserves history
- **Given**: Completed sessions exist in storage
- **When**: The server starts
- **Then**: Historical sessions appear in the interaction list

### Requirement: REQ-PERSIST-03 Retention Policy
The system MUST automatically clean up sessions based on retention policy.

#### Scenario: Expired sessions removed
- **Given**: Sessions older than retention period exist
- **When**: Cleanup runs (on startup or periodically)
- **Then**: Expired sessions are removed from storage

### Requirement: REQ-PERSIST-04 Session Count Limit
The system MUST enforce a maximum session count limit.

#### Scenario: Oldest sessions removed when limit exceeded
- **Given**: Number of stored sessions equals max limit
- **When**: A new session is saved
- **Then**: The oldest session is removed to make room

## MODIFIED Requirements

### Requirement: REQ-INTERACTION-LIST Interaction List Includes History
The interaction list endpoint MUST include persisted historical sessions.

#### Scenario: Historical sessions in list
- **Given**: Persisted sessions exist in storage
- **When**: Client requests interaction list
- **Then**: Response includes both active and historical sessions (limited to configured count)
