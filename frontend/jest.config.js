module.exports = {
  testEnvironment: "jsdom",
  setupFilesAfterEnv: ["<rootDir>/tests/setup.js"],
  testMatch: ["<rootDir>/tests/**/*.test.js"],
  moduleNameMapper: {
    "\\.module\\.css$": "<rootDir>/tests/mocks/style.mock.js",
  },
  transform: {
    "^.+\\.(js|jsx)$": "babel-jest",
  },
};
