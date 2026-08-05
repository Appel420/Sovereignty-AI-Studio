#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Capability {
    ObserveEvidence,
    Analyze,
    GenerateOutput,
    Verify,
    Report,
}

impl Capability {
    pub const fn name(self) -> &'static str {
        match self {
            Self::ObserveEvidence => "ObserveEvidence",
            Self::Analyze => "Analyze",
            Self::GenerateOutput => "GenerateOutput",
            Self::Verify => "Verify",
            Self::Report => "Report",
        }
    }
}
