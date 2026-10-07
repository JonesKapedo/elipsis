import { Routes, Route } from "react-router-dom";
import { Home } from "./routes/index";
import { Login } from "./routes/login";
import { AppShell } from "./routes/app/route";
import { AssessmentsList } from "./routes/app/assessments/index";
import { AssessmentsNew } from "./routes/app/assessments/new";
import { AssessmentResult } from "./routes/app/assessments/$id/results";
import { AssessmentReport } from "./routes/app/assessments/$id/report";
import { Automation } from "./routes/app/automation";
import { Roadmap } from "./routes/app/roadmap";
import { Roi } from "./routes/app/roi";
import { Benchmarks } from "./routes/app/benchmarks";
import { Advisor } from "./routes/app/advisor";
import { Departments } from "./routes/app/departments";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<Login />} />
      <Route path="/app" element={<AppShell />}>
        <Route index element={<AssessmentsList />} />
        <Route path="assessments">
          <Route index element={<AssessmentsList />} />
          <Route path="new" element={<AssessmentsNew />} />
          <Route path=":$id">
            <Route path="results" element={<AssessmentResult />} />
            <Route path="report" element={<AssessmentReport />} />
          </Route>
        </Route>
        <Route path="automation" element={<Automation />} />
        <Route path="roadmap" element={<Roadmap />} />
        <Route path="roi" element={<Roi />} />
        <Route path="benchmarks" element={<Benchmarks />} />
        <Route path="advisor" element={<Advisor />} />
        <Route path="departments" element={<Departments />} />
      </Route>
    </Routes>
  );
}
