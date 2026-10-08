# Getting Started with Create React App

This project was bootstrapped with [Create React App](https://github.com/facebook/create-react-app).

## Available Scripts

In the project directory, you can run:

### `npm start`

Runs the app in the development mode.\
Open [http://localhost:3000](http://localhost:3000) to view it in your browser.

The page will reload when you make changes.\
You may also see any lint errors in the console.

### `npm test`

Launches the test runner in the interactive watch mode.\
See the section about [running tests](https://facebook.github.io/create-react-app/docs/running-tests) for more information.

### `npm run build`

Builds the app for production to the `build` folder.\
It correctly bundles React in production mode and optimizes the build for the best performance.

The build is minified and the filenames include the hashes.\
Your app is ready to be deployed!

See the section about [deployment](https://facebook.github.io/create-react-app/docs/deployment) for more information.

### `npm run eject`

**Note: this is a one-way operation. Once you `eject`, you can't go back!**

If you aren't satisfied with the build tool and configuration choices, you can `eject` at any time. This command will remove the single build dependency from your project.

Instead, it will copy all the configuration files and the transitive dependencies (webpack, Babel, ESLint, etc) right into your project so you have full control over them. All of the commands except `eject` will still work, but they will point to the copied scripts so you can tweak them. At this point you're on your own.

You don't have to ever use `eject`. The curated feature set is suitable for small and middle deployments, and you shouldn't feel obligated to use this feature. However we understand that this tool wouldn't be useful if you couldn't customize it when you are ready for it.

## Learn More

You can learn more in the [Create React App documentation](https://facebook.github.io/create-react-app/docs/getting-started).

To learn React, check out the [React documentation](https://reactjs.org/).

### Code Splitting

This section has moved here: [https://facebook.github.io/create-react-app/docs/code-splitting](https://facebook.github.io/create-react-app/docs/code-splitting)

### Analyzing the Bundle Size

This section has moved here: [https://facebook.github.io/create-react-app/docs/analyzing-the-bundle-size](https://facebook.github.io/create-react-app/docs/analyzing-the-bundle-size)

### Making a Progressive Web App

This section has moved here: [https://facebook.github.io/create-react-app/docs/making-a-progressive-web-app](https://facebook.github.io/create-react-app/docs/making-a-progressive-web-app)

### Advanced Configuration

This section has moved here: [https://facebook.github.io/create-react-app/docs/advanced-configuration](https://facebook.github.io/create-react-app/docs/advanced-configuration)

### Deployment

This section has moved here: [https://facebook.github.io/create-react-app/docs/deployment](https://facebook.github.io/create-react-app/docs/deployment)

### `npm run build` fails to minify

This section has moved here: [https://facebook.github.io/create-react-app/docs/troubleshooting#npm-run-build-fails-to-minify](https://facebook.github.io/create-react-app/docs/troubleshooting#npm-run-build-fails-to-minify)

### Station map tiles

The station map defaults to OpenStreetMap Standard tiles, without an API key.
The same light basemap is used in both application themes.
To change providers, set `REACT_APP_MAP_TILE_URL`, optionally
`REACT_APP_MAP_TILE_DARK_URL`, and `REACT_APP_MAP_TILE_ATTRIBUTION` before building.
Attribution must credit the selected provider and its underlying data sources.
These values are public build-time configuration; never include secret keys.
Review your provider's usage terms and capacity before production deployment.

Location is requested once per map mount (HTTPS or localhost required), remains
in component memory, and is not sent to the Voltx API. Distances are straight-line,
not driving routes. Station updates use the existing parent query; the map adds
no polling or subscriptions.

The public OpenStreetMap Standard endpoint is a development/MVP fallback.
Configure a suitable production tile provider with `REACT_APP_MAP_TILE_URL`
and `REACT_APP_MAP_ATTRIBUTION` (the older `REACT_APP_MAP_TILE_ATTRIBUTION` also
remains supported). Both themes use the same tiles unless a dark URL is supplied.
All these variables are public build-time values; never include private keys.

Customer discovery counts “nearby” as within 10 km straight-line distance when
location is available. Other counts describe the loaded station dataset, not the
entire network. Scan QR currently provides a manual station-code fallback; camera
scanning is not implemented. Backend demo chargers remain explicitly opt-in and
are independent of the frontend production build.

### Customer sign-in

The phone → OTP → optional registration flow uses the existing AuthContext.
Axios sends cookies with `withCredentials`; the browser never reads session JWTs.
Legacy `ev_token` entries are removed, and users sign in again once after upgrade.
The query cache is cleared between customers. New accounts start with a zero wallet
and empty history, with the existing discovery dashboard unchanged.

Local demo controls require `REACT_APP_DEMO_AUTH=true` and a nonproduction build.
The backend separately requires `OTP_MODE=demo`; optional code responses require
`EXPOSE_DEMO_OTP=true`. Restart CRA after changing `.env`. Production builds strip
the demo controls even if the flag is accidentally set. See `backend/AUTH.md` for
trusted origins, cookie settings, SMS integration, migration, and tests.
