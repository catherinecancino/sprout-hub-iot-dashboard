import { initializeApp } from "firebase/app";
import { getFirestore } from "firebase/firestore";

// Your web app's Firebase configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
  apiKey: "AIzaSyB-vyfhao6RCcRicoeeIvUie1xUaVuNSck",
  authDomain: "agritech-iot-847f1.firebaseapp.com",
  projectId: "agritech-iot-847f1",
  storageBucket: "agritech-iot-847f1.firebasestorage.app",
  messagingSenderId: "13950436854",
  appId: "1:13950436854:web:b260b699c989327479b3d7",
  measurementId: "G-XGL09Q2FXY"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
export const db = getFirestore(app);