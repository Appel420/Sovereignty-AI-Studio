#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum NetworkBoundary {
    Offline,
    LocalOnly,
    AirGappedImport,
    AuthorizedExternal,
}

impl NetworkBoundary {
    pub const fn permits_external_network(self) -> bool {
        matches!(self, Self::AuthorizedExternal)
    }
}
