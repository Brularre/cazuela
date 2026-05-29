import "@testing-library/jest-dom";

jest.mock("next/router", () => ({
  useRouter: () => ({ push: jest.fn(), pathname: "/" }),
}));
